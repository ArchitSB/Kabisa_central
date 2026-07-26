import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

type PaginationProps = {
  page: number;
  pageCount: number;
  canPrevious: boolean;
  canNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
};

export function Pagination({
  page,
  pageCount,
  canPrevious,
  canNext,
  onPrevious,
  onNext,
}: PaginationProps) {
  return (
    <div className="flex items-center justify-between gap-4 px-1 pt-4">
      <p className="text-xs text-secondary">
        Page <strong className="numeric text-foreground">{page}</strong> of{" "}
        <strong className="numeric text-foreground">{Math.max(pageCount, 1)}</strong>
      </p>
      <div className="flex items-center gap-2">
        <Button
          aria-label="Previous page"
          variant="secondary"
          size="icon"
          className="size-9 min-h-9"
          disabled={!canPrevious}
          onClick={onPrevious}
        >
          <ChevronLeft aria-hidden="true" />
        </Button>
        <Button
          aria-label="Next page"
          variant="secondary"
          size="icon"
          className="size-9 min-h-9"
          disabled={!canNext}
          onClick={onNext}
        >
          <ChevronRight aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
