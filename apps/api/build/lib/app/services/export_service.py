# ruff: noqa: E501

import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal
from html import escape
from typing import Any

from fastapi.responses import StreamingResponse

from app.schemas.reporting import ReportMeta


def _display(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    return value


def letterhead_rows(meta: ReportMeta, title: str) -> list[list[Any]]:
    contacts = " · ".join(value for value in (meta.phone, meta.email) if value)
    return [
        [meta.company_name],
        [title],
        [f"TIN: {meta.tin or '—'}"],
        [meta.postal or ""],
        [contacts],
        [f"Currency: {meta.currency}", f"Generated: {meta.generated_at.isoformat()}"],
        [],
    ]


def build_csv(
    *,
    meta: ReportMeta,
    title: str,
    headers: list[str],
    rows: list[list[Any]],
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerows(letterhead_rows(meta, title))
    writer.writerow(headers)
    writer.writerows([[_display(value) for value in row] for row in rows])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def _cell(reference: str, value: Any, style: int = 0) -> str:
    value = _display(value)
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f'<c r="{reference}"{style_attr}><v>{value}</v></c>'
    return (
        f'<c r="{reference}" t="inlineStr"{style_attr}><is><t xml:space="preserve">'
        f"{escape(str(value))}</t></is></c>"
    )


def _column_name(index: int) -> str:
    name = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(65 + remainder) + name
    return name


def build_xlsx(
    *,
    meta: ReportMeta,
    title: str,
    headers: list[str],
    rows: list[list[Any]],
) -> bytes:
    sheet_rows = letterhead_rows(meta, title) + [headers] + rows
    xml_rows = []
    header_row_number = len(letterhead_rows(meta, title)) + 1
    for row_number, row in enumerate(sheet_rows, start=1):
        style = 1 if row_number in {1, 2, header_row_number} else 0
        cells = "".join(
            _cell(f"{_column_name(column)}{row_number}", value, style)
            for column, value in enumerate(row, start=1)
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    last_column = _column_name(max(len(headers), 1))
    worksheet = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{last_column}{max(len(sheet_rows), 1)}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="{header_row_number}" topLeftCell="A{header_row_number + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <sheetData>{''.join(xml_rows)}</sheetData>
  <autoFilter ref="A{header_row_number}:{last_column}{max(len(sheet_rows), header_row_number)}"/>
</worksheet>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Inter"/></font><font><b/><color rgb="FF244A5C"/><sz val="11"/><name val="Inter"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def download_response(
    *,
    export: str,
    title: str,
    filename: str,
    meta: ReportMeta,
    headers: list[str],
    rows: list[list[Any]],
) -> StreamingResponse:
    if export == "xlsx":
        content = build_xlsx(meta=meta, title=title, headers=headers, rows=rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = build_csv(meta=meta, title=title, headers=headers, rows=rows)
        media_type = "text/csv; charset=utf-8"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{export}"'},
    )
