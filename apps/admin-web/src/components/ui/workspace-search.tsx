import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUpRight, Search, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/features/auth/auth-store";
import { navigation } from "@/lib/navigation";

export function WorkspaceSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const items = navigation
    .flatMap((s) => s.items)
    .filter(
      (i) =>
        (!i.permission || hasPermission(i.permission)) &&
        i.label.toLowerCase().includes(query.toLowerCase().trim()),
    );
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((value) => !value);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) setQuery("");
      }}
    >
      <Dialog.Trigger
        className="ops-search-trigger"
        aria-label="Find a workspace"
        aria-keyshortcuts="Control+k Meta+k"
      >
        <Search size={16} />
        <span>Go to a workspace…</span>
        <kbd>Ctrl K</kbd>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="ops-command-overlay" />
        <Dialog.Content className="ops-command">
          <Dialog.Title>Where would you like to go?</Dialog.Title>
          <Dialog.Description>Find an area of your Kabisa workspace.</Dialog.Description>
          <Dialog.Close className="ops-command-close" aria-label="Close workspace search">
            <X size={20} />
          </Dialog.Close>
          <div className="ops-command-input">
            <Search size={20} />
            <input
              aria-label="Search workspaces"
              placeholder="Search orders, inventory, customers…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && items[0]) {
                  navigate(items[0].href);
                  setOpen(false);
                  setQuery("");
                }
              }}
            />
          </div>
          <nav aria-label="Workspace search results" className="ops-command-results">
            {items.map((item) => (
              <button
                key={item.href}
                onClick={() => {
                  navigate(item.href);
                  setOpen(false);
                  setQuery("");
                }}
              >
                <item.icon size={18} />
                <span>{item.label}</span>
                <ArrowUpRight size={16} />
              </button>
            ))}
            {!items.length && <p>No matching workspace. Try another name.</p>}
          </nav>
          <div className="ops-command-footer">
            Tab to move · Enter to open · Esc to close
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
