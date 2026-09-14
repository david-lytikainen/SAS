import { FormEvent, useEffect, useMemo, useState } from "react";
import { ExternalLink, Link, Plus, Trash2 } from "lucide-react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type SavedSite = {
  id: string;
  name: string;
  url: string;
};

const storageKey = "site-shelf-sites";

function readSites(): SavedSite[] {
  try {
    const saved = localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function normalizeUrl(value: string) {
  const candidate = value.trim();
  return candidate.match(/^https?:\/\//i) ? candidate : `https://${candidate}`;
}

function getSiteName(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function App() {
  const [sites, setSites] = useState<SavedSite[]>(readSites);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(sites));
  }, [sites]);

  const hasSites = sites.length > 0;
  const orderedSites = useMemo(() => [...sites].reverse(), [sites]);

  function addSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUrl = normalizeUrl(url);

    try {
      const parsed = new URL(normalizedUrl);
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
      if (sites.some((site) => site.url === normalizedUrl)) {
        setError("That link is already on your shelf.");
        return;
      }
      setSites((current) => [...current, { id: crypto.randomUUID(), name: getSiteName(normalizedUrl), url: normalizedUrl }]);
      setUrl("");
      setError("");
    } catch {
      setError("Enter a complete website address.");
    }
  }

  function removeSite(id: string) {
    setSites((current) => current.filter((site) => site.id !== id));
  }

  return (
    <main>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="/">Site Shelf</a>
          <span className="site-count">{sites.length} saved</span>
        </div>
      </header>

      <section className="page-shell" aria-labelledby="page-title">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Your work</p>
            <h1 id="page-title">Keep your sites close.</h1>
          </div>
          <p className="intro">Add a link and keep a live preview of the work you have built in one calm place.</p>
        </div>

        <form className="add-site" onSubmit={addSite}>
          <label htmlFor="site-url">Website link</label>
          <div className="url-row">
            <div className="url-input-wrap">
              <Link aria-hidden="true" size={19} />
              <input
                id="site-url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="example.com"
                type="url"
                inputMode="url"
                autoCapitalize="none"
                autoCorrect="off"
              />
            </div>
            <button className="primary-button" type="submit">
              <Plus size={18} aria-hidden="true" />
              Add site
            </button>
          </div>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
        </form>

        {hasSites ? (
          <section className="site-grid" aria-label="Saved sites">
            {orderedSites.map((site) => (
              <article className="site-card" key={site.id}>
                <div className="card-header">
                  <div>
                    <h2>{site.name}</h2>
                    <a href={site.url} target="_blank" rel="noreferrer">{site.url}</a>
                  </div>
                  <div className="card-actions">
                    <a className="icon-button" href={site.url} target="_blank" rel="noreferrer" aria-label={`Open ${site.name} in a new tab`} title="Open site">
                      <ExternalLink size={18} aria-hidden="true" />
                    </a>
                    <button className="icon-button danger-button" type="button" onClick={() => removeSite(site.id)} aria-label={`Remove ${site.name}`} title="Remove site">
                      <Trash2 size={18} aria-hidden="true" />
                    </button>
                  </div>
                </div>
                <div className="preview-frame">
                  <iframe title={`${site.name} preview`} src={site.url} loading="lazy" />
                </div>
              </article>
            ))}
          </section>
        ) : (
          <section className="empty-state" aria-label="No saved sites">
            <Link size={28} aria-hidden="true" />
            <h2>Your shelf is empty.</h2>
            <p>Add the first site you built above.</p>
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
