"use client";
import { useState } from "react";
import { BookOpen, Plus, Pencil, Trash2 } from "lucide-react";
import { api, query, useData, date, categoryName } from "@/lib/api";
import type { Article, Workspace } from "@/lib/types";

import { Button, Title, Empty, Feedback, SearchBox, Select, Modal } from "./common";

export function Knowledge({ meta, toast }: { meta: Workspace; toast: (message: string) => void }) {
  const [q, search] = useState(""),
    [category, setCat] = useState(""),
    [mode, setMode] = useState(""),
    [busy, wait] = useState(false),
    [err, fail] = useState("");
  const blank = {
    id: 0,
    title: "",
    category: meta.categories[0],
    issue: "",
    steps: "",
    resolution: "",
    updated_at: "",
  };
  const [draft, edit] = useState<Article>(blank);
  const { data, error, reload } = useData<Article[]>("knowledge?" + query({ q, category }));
  const open = (m: string, a: Article) => {
    edit(a);
    setMode(m);
    fail("");
  };
  async function commit() {
    wait(true);
    fail("");
    try {
      if (mode === "Delete article") await api("knowledge/" + draft.id, "DELETE");
      else {
        const { title, issue, steps, resolution, category } = draft;
        await api("knowledge" + (draft.id ? "/" + draft.id : ""), draft.id ? "PUT" : "POST", {
          title,
          issue,
          steps,
          resolution,
          category,
        });
      }
      setMode("");
      reload();
      toast(mode === "Delete article" ? "Article deleted" : "Article saved");
    } catch (e) {
      fail((e as Error).message);
    } finally {
      wait(false);
    }
  }
  return (
    <>
      <Title
        title="Knowledge base"
        sub="Capture known issues, troubleshooting steps, and approved resolutions."
      >
        <Button variant="default" onClick={() => open("Create article", blank)}>
          <Plus size={16} />
          Create article
        </Button>
      </Title>
      <section className="card">
        <div className="table-tools">
          <SearchBox placeholder="Search articles" value={q} onChange={search} />
          <Select
            label="Category"
            all="All categories"
            options={meta.categories}
            value={category}
            onChange={setCat}
          />
        </div>
        {!data ? (
          <Feedback error={error} reload={reload} />
        ) : data.length ? (
          data.map((a) => (
            <details className="article" key={a.id}>
              <summary>
                <BookOpen size={17} />
                {a.title}
                <span className="badge grey">{categoryName(a.category)}</span>
              </summary>
              <small>Updated {date(a.updated_at, true)}</small>
              <h3>Known issue</h3>
              <p>{a.issue}</p>
              <h3>Troubleshooting steps</h3>
              <p>{a.steps}</p>
              <h3>Approved resolution</h3>
              <p>{a.resolution || "None recorded"}</p>
              <div className="actions">
                <Button onClick={() => open("Edit article", a)}>
                  <Pencil size={15} />
                  Edit
                </Button>
                <Button onClick={() => open("Delete article", a)}>
                  <Trash2 size={15} />
                  Delete
                </Button>
              </div>
            </details>
          ))
        ) : (
          <Empty
            text={
              q || category
                ? "No articles match these filters"
                : "No articles yet. Create an article to share a verified support procedure."
            }
          />
        )}
      </section>
      {mode && (
        <Modal
          title={mode}
          close={() => {
            if (!busy) setMode("");
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              commit();
            }}
          >
            {mode === "Delete article" ? (
              <p>Delete “{draft.title}” from the knowledge base?</p>
            ) : (
              <>
                <label className="field">
                  Title
                  <input
                    required
                    maxLength={200}
                    value={draft.title}
                    onChange={(e) => edit({ ...draft, title: e.target.value })}
                  />
                </label>
                <Select
                  label="Category"
                  options={meta.categories}
                  value={draft.category}
                  onChange={(category) => edit({ ...draft, category })}
                />
                {(["issue", "steps", "resolution"] as const).map((k, i) => (
                  <label className="field" key={k}>
                    {["Known issue", "Troubleshooting steps", "Approved resolution (optional)"][i]}
                    <textarea
                      required={k !== "resolution"}
                      maxLength={8000}
                      value={draft[k]}
                      onChange={(e) => edit({ ...draft, [k]: e.target.value })}
                    />
                  </label>
                ))}
              </>
            )}
            {err && <p className="error">{err}</p>}
            <div className="actions end">
              <Button type="button" disabled={busy} onClick={() => setMode("")}>
                Cancel
              </Button>
              <Button variant={mode === "Delete article" ? "danger" : "default"} disabled={busy}>
                {mode === "Delete article" ? "Delete article" : "Save article"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
