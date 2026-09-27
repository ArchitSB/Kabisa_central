import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, ClipboardList, Search, Zap } from "lucide-react";
import { toast } from "sonner";
import { parseQuickOrder } from "@kabisa/core";
import type { Page, Product } from "@kabisa/api-client";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import { useSeo } from "../lib/seo";
import { t } from "../i18n";
import { AsyncButton, Empty, PageIntro, Quantity } from "../components/ui";
type Match = {
  line: number;
  query: string;
  quantity: number;
  products: Product[];
  selected: string;
  error?: string;
};
export default function QuickOrder() {
  const [input, setInput] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);
  const [added, setAdded] = useState(false);
  const { authenticated, add, refresh } = useStore();
  useSeo(t("nav.quick"));
  async function match() {
    setAdded(false);
    const lines = parseQuickOrder(input);
    const result: Match[] = [];
    for (let i = 0; i < lines.length; i += 5) {
      result.push(
        ...(await Promise.all(
          lines.slice(i, i + 5).map(async (line) => {
            if (line.error) return { ...line, products: [], selected: "" };
            const data = await api.get<Page<Product>>(
              `/catalog/products?search=${encodeURIComponent(line.query)}&page_size=8`,
            );
            const exact = data.items.find(
              (p) =>
                p.sku.toLowerCase() === line.query.toLowerCase() ||
                p.name.toLowerCase() === line.query.toLowerCase(),
            );
            return {
              ...line,
              products: data.items,
              selected:
                exact?.id || (data.items.length === 1 ? data.items[0].id : ""),
            };
          }),
        )),
      );
    }
    setMatches(result);
  }
  const selected = matches.filter((m) => m.selected && !m.error);
  async function addAll() {
    if (authenticated) {
      const quantities = new Map<string, number>();
      for (const m of selected)
        quantities.set(
          m.selected,
          (quantities.get(m.selected) || 0) + m.quantity,
        );
      await api.post("/cart/merge", {
        items: [...quantities].map(([product_id, quantity]) => ({
          product_id,
          quantity,
        })),
      });
      await refresh();
      toast.success(t("action.added"));
    } else {
      for (const m of selected)
        await add(
          m.products.find((p) => p.id === m.selected)!,
          m.quantity,
        );
    }
    setAdded(true);
  }
  return (
    <div className="container quick-page">
      <PageIntro
        eyebrow={t("nav.quick")}
        title={t("quick.title")}
        body={t("quick.subtitle")}
      />
      <div className="quick-layout">
        <section className="panel quick-input-panel">
          <p className="eyebrow">{t("quick.step1")}</p>
          <label className="field">
            <span>{t("quick.label")}</span>
            <textarea
              rows={12}
              placeholder={t("quick.placeholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={20000}
            />
          </label>
          <p className="muted small">{t("quick.hint")}</p>
          <AsyncButton action={match} disabled={!input.trim()}>
            <Search size={17} />
            {t("quick.match")}
          </AsyncButton>
          <div className="quick-tip">
            <Zap size={19} />
            <p>{t("quick.review")}</p>
          </div>
        </section>
        <section className="panel quick-matches">
          <p className="eyebrow">{t("quick.step2")}</p>
          {matches.length ? (
            <>
              <div className="matches-list">
                {matches.map((m, index) => (
                  <div className="match-row" key={m.line}>
                    <span
                      className={`match-index ${m.selected ? "matched" : ""}`}
                    >
                      {m.selected ? (
                        <Check size={16} />
                      ) : (
                        String(m.line).padStart(2, "0")
                      )}
                    </span>
                    <div>
                      <strong>{m.query}</strong>
                      {m.error ? (
                        <p className="error-text">{t("quick.invalid")}</p>
                      ) : m.products.length ? (
                        <select
                          aria-label={`${t("quick.choose")}: ${m.query}`}
                          value={m.selected}
                          onChange={(e) =>
                            setMatches((previous) =>
                              previous.map((r, i) =>
                                i === index
                                  ? { ...r, selected: e.target.value }
                                  : r,
                              ),
                            )
                          }
                        >
                          <option value="">{t("quick.choose")}</option>
                          {m.products.map((p) => (
                            <option
                              value={p.id}
                              key={p.id}
                              disabled={p.availability === "OUT_OF_STOCK"}
                            >
                              {p.name} · {p.sku}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <p className="error-text">{t("quick.noMatch")}</p>
                      )}
                    </div>
                    <Quantity
                      value={m.quantity}
                      onChange={(quantity) =>
                        setMatches((previous) =>
                          previous.map((r, i) =>
                            i === index ? { ...r, quantity } : r,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </div>
              <div className="matches-footer">
                <span>
                  {selected.length} / {matches.length} {t("quick.matched")}
                </span>
                {added ? (
                  <Link className="btn" to="/cart">
                    {t("nav.cart")}
                    <ArrowRight size={17} />
                  </Link>
                ) : (
                  <AsyncButton action={addAll} disabled={!selected.length}>
                    {t("quick.addAll")}
                    <ArrowRight size={17} />
                  </AsyncButton>
                )}
              </div>
            </>
          ) : (
            <Empty
              title={t("quick.empty")}
              body={t("quick.emptyBody")}
              icon={<ClipboardList size={34} strokeWidth={1.3} />}
            />
          )}
        </section>
      </div>
    </div>
  );
}
