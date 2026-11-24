"use client";
import { useEffect, useRef, useState } from "react";
import type { Filters, Workspace } from "@/lib/types";
import { SlidersHorizontal, X, LoaderCircle, Inbox, Search, TriangleAlert } from "lucide-react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
const variants = cva("btn", {
  variants: {
    variant: {
      default: "primary",
      outline: "outline",
      ghost: "ghost",
      danger: "danger",
    },
  },
  defaultVariants: { variant: "outline" },
});
export function Button({
  asChild,
  variant,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof variants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component className={variants({ variant, className })} {...props} />;
}

export function Feedback({ error, reload }: { error?: string; reload?: () => void }) {
  return (
    <div className="feedback" role="status">
      {error ? (
        <>
          <TriangleAlert />
          {error}
          {reload && <Button onClick={reload}>Retry</Button>}
        </>
      ) : (
        <>
          <LoaderCircle className="spin" />
          Loading workspace…
        </>
      )}
    </div>
  );
}
export function Empty({ text }: { text: string }) {
  return (
    <div className="feedback">
      <Inbox />
      {text}
    </div>
  );
}
export function Title({
  title,
  sub,
  children,
}: {
  title: string;
  sub: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      <div className="actions">{children}</div>
    </div>
  );
}
export function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const node = ref.current;
    node?.showModal();
    return () => node?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={close}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <div className="dialog-inner">
        <div className="row between">
          <h2>{title}</h2>
          <Button variant="ghost" aria-label="Close dialog" onClick={close}>
            <X size={18} />
          </Button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
export function Select({
  label,
  value,
  options,
  onChange,
  all,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  all?: string;
}) {
  return (
    <label className="field">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {all && <option value="">{all}</option>}
        {options.map((x) => (
          <option key={x}>{x}</option>
        ))}
      </select>
    </label>
  );
}
export function FilterBar({
  meta,
  filters,
  set,
}: {
  meta: Workspace;
  filters: Filters;
  set: (v: Filters) => void;
}) {
  const [open, show] = useState(false);
  const [draft, edit] = useState(filters);
  const options = {
    client: meta.clients,
    category: meta.categories,
    priority: meta.priorities,
    status: meta.statuses,
  };
  function change(key: string, value: string) {
    edit({ ...draft, [key]: value });
  }
  const count = Object.values(filters).filter(Boolean).length;
  return (
    <>
      <Button
        onClick={() => {
          edit(filters);
          show(true);
        }}
      >
        <SlidersHorizontal size={15} />
        Filters{count ? " (" + count + ")" : ""}
      </Button>
      {open && (
        <Modal title="Filter tickets" close={() => show(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              set(draft);
              show(false);
            }}
          >
            <div className="form-grid">
              {Object.entries(options).map(([key, values]) => (
                <Select
                  key={key}
                  label={key}
                  options={values}
                  all="All"
                  value={draft[key] || ""}
                  onChange={(v) => change(key, v)}
                />
              ))}
              <label className="field">
                Created from
                <input
                  type="date"
                  max={draft.end}
                  value={draft.start || ""}
                  onChange={(e) => change("start", e.target.value)}
                />
              </label>
              <label className="field">
                Created through
                <input
                  type="date"
                  min={draft.start}
                  value={draft.end || ""}
                  onChange={(e) => change("end", e.target.value)}
                />
              </label>
            </div>
            <div className="actions end">
              <Button
                type="button"
                onClick={() => {
                  set({});
                  show(false);
                }}
              >
                Clear filters
              </Button>
              <Button variant="default">Apply filters</Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (s: string) => void;
  placeholder: string;
}) {
  return (
    <label className="searchbox">
      <Search size={16} />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
export function Badge({ value }: { value: string }) {
  return (
    <span
      className={
        "badge " +
        (value.includes("Engineering") || value === "P2"
          ? "amber"
          : value === "Closed"
            ? "green"
            : value === "P1"
              ? "red"
              : value === "P4"
                ? "grey"
                : "blue")
      }
    >
      {value === "Open - with L1"
        ? "Open · L1"
        : value === "Open - with Engineering"
          ? "Escalated"
          : value === "Closed"
            ? "Resolved"
            : value}
    </span>
  );
}
export function Pages({
  page,
  total,
  go,
  size = 20,
}: {
  page: number;
  total: number;
  go: (n: number) => void;
  size?: number;
}) {
  return (
    <div className="pager">
      <span>
        {total ? (page - 1) * size + 1 + "–" + Math.min(total, page * size) : "0"} of{" "}
        {total.toLocaleString()}
      </span>
      <div className="actions">
        <Button disabled={page <= 1} onClick={() => go(page - 1)}>
          Previous
        </Button>
        <Button disabled={page * size >= total} onClick={() => go(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
