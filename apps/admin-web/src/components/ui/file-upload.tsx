import { useId, useRef, useState } from "react";
import { FileSpreadsheet, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type FileUploadProps = {
  accept: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  label?: string;
  hint?: string;
};

export function FileUpload({
  accept,
  file,
  onFileChange,
  label = "Choose a file",
  hint = "Select a file from your device.",
}: FileUploadProps) {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function acceptFiles(files: FileList | null) {
    onFileChange(files?.item(0) ?? null);
  }

  return (
    <div>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(event) => acceptFiles(event.target.files)}
      />
      <div
        className={cn(
          "rounded-card border border-dashed border-primary-300 bg-primary-50/50 p-6 text-center transition-colors duration-standard",
          dragging && "border-primary-600 bg-primary-100",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          acceptFiles(event.dataTransfer.files);
        }}
      >
        <span className="mx-auto flex size-11 items-center justify-center rounded-full bg-surface text-primary-700 shadow-sm">
          <UploadCloud aria-hidden="true" className="size-5" />
        </span>
        <label
          htmlFor={id}
          className="mt-3 inline-block text-sm font-semibold text-primary-800"
        >
          {label}
        </label>
        <p className="mt-1 text-xs text-secondary">{hint}</p>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => inputRef.current?.click()}
        >
          Browse files
        </Button>
      </div>
      {file ? (
        <div className="mt-3 flex items-center gap-3 rounded-control border border-border bg-surface p-3">
          <FileSpreadsheet
            aria-hidden="true"
            className="size-5 shrink-0 text-primary-700"
          />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">{file.name}</span>
            <span className="text-xs text-secondary">
              {Math.max(1, Math.round(file.size / 1024))} KB
            </span>
          </span>
          <button
            type="button"
            aria-label={`Remove ${file.name}`}
            className="flex size-9 items-center justify-center rounded-control text-secondary transition-colors hover:bg-danger-surface hover:text-danger"
            onClick={() => {
              if (inputRef.current) inputRef.current.value = "";
              onFileChange(null);
            }}
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
      ) : null}
    </div>
  );
}
