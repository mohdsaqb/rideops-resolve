"use client";

import { useEffect, useState } from "react";
import { BookOpen, ChartColumn, Inbox, Route, Menu, PanelLeftClose } from "lucide-react";
import { TicketQueue } from "@/components/TicketQueue";
import { TicketDetail } from "@/components/Ticket";
import { Reports } from "@/components/Reports";
import { Knowledge } from "@/components/workspaces";
import { Feedback } from "@/components/common";
import { useData } from "@/lib/api";
import type { Workspace } from "@/lib/types";

const navigation = [
  { id: "tickets", label: "Ticket queue", icon: Inbox },
  { id: "knowledge", label: "Knowledge base", icon: BookOpen },
  { id: "reports", label: "Operations dashboard", icon: ChartColumn },
];
const oldPages: Record<string, string> = {
  escalations: "tickets",
  overview: "reports",
  analytics: "reports",
  triage: "tickets",
  settings: "reports",
};

export default function Page() {
  const [path, setPath] = useState("tickets");
  const [menuOpen, setMenuOpen] = useState(false);
  const [message, setMessage] = useState("");
  const workspace = useData<Workspace>("workspace");
  useEffect(() => {
    function followLink() {
      setMenuOpen(false);
      setPath(location.hash.slice(1) || "tickets");
      window.scrollTo(0, 0);
    }
    followLink();
    window.addEventListener("hashchange", followLink);
    return () => window.removeEventListener("hashchange", followLink);
  }, []);
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 4500);
    return () => clearTimeout(timer);
  }, [message]);

  const [route, id, tab] = path.split("/");
  const screen = oldPages[route] || route;
  function content() {
    const meta = workspace.data;
    if (!meta) return <Feedback error={workspace.error} reload={workspace.reload} />;
    switch (screen) {
      case "ticket":
        return <TicketDetail key={id} id={id} initial={tab} meta={meta} toast={setMessage} />;
      case "knowledge":
        return <Knowledge meta={meta} toast={setMessage} />;
      case "reports":
        return <Reports meta={meta} showSettings={route === "settings"} />;
      default:
        return <TicketQueue meta={meta} />;
    }
  }
  return (
    <>
      <aside className="sidebar">
        <a className="brand" href="#tickets">
          <Route size={23} /> RideOps Resolve
        </a>
        <button
          className="menu-toggle"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          aria-controls="workspace-nav"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <PanelLeftClose size={20} /> : <Menu size={20} />}
        </button>
        <nav id="workspace-nav" className={menuOpen ? "expanded" : ""} aria-label="Workspace">
          {navigation.map(({ id, label, icon: Icon }) => (
            <a
              key={id}
              href={"#" + id}
              onClick={() => setMenuOpen(false)}
              aria-current={(screen === "ticket" ? "tickets" : screen) === id ? "page" : undefined}
            >
              <Icon size={16} />
              {label}
            </a>
          ))}
        </nav>
        <div className="service-state">
          <span />{" "}
          {workspace.data
            ? workspace.data.groq_configured
              ? "Groq configured"
              : "Predefined rules active"
            : "Support workspace"}
        </div>
      </aside>
      <main>{content()}</main>
      {message && (
        <div role="status" className="toast">
          {message}
        </div>
      )}
    </>
  );
}
