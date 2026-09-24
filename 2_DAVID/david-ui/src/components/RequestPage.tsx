import { FormEvent, useCallback, useEffect, useState } from "react";

import { requestApi, WebsiteRequest } from "../api";

type Props = { requestNumber: string; token: string; onBack: () => void };
const statuses = ["submitted", "reviewing", "in_progress", "delivered"];

export default function RequestPage({ requestNumber, token, onBack }: Props) {
  const [request, setRequest] = useState<WebsiteRequest | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => { setLoading(true); try { setRequest(await requestApi.get(requestNumber, token)); setError(""); } catch (nextError) { setError(nextError instanceof Error ? nextError.message : "Unable to load request."); } finally { setLoading(false); } }, [requestNumber, token]);
  useEffect(() => { void load(); }, [load]);
  const submitComment = async (event: FormEvent) => { event.preventDefault(); if (!message.trim()) return; try { await requestApi.comment(requestNumber, message, token); setMessage(""); await load(); } catch (nextError) { setError(nextError instanceof Error ? nextError.message : "Unable to send message."); } };
  const updateStatus = async (status: string) => { try { setRequest(await requestApi.status(token, requestNumber, status)); } catch (nextError) { setError(nextError instanceof Error ? nextError.message : "Unable to update status."); } };
  if (loading) return <p className="section-copy">Loading request...</p>;
  if (!request) return <p className="error">{error}</p>;
  return <section className="section"><button className="text-button" type="button" onClick={onBack}>Back to work</button><div className="panel"><p className="eyebrow">Website request {request.requestNumber}</p><h2>{request.projectDescription}</h2><div className="request-meta"><div><strong>Status</strong>{request.status.replace("_", " ")}</div><div><strong>Target date</strong>{request.targetDate}</div><div><strong>Budget</strong>{request.budgetRange}</div></div>{request.viewerIsAdmin ? <label>Status<select value={request.status} onChange={(event) => void updateStatus(event.target.value)}>{statuses.map((status) => <option key={status} value={status}>{status.replace("_", " ")}</option>)}</select></label> : null}<h3>Messages</h3>{request.comments.length ? request.comments.map((comment) => <article className="comment" key={comment.id}><strong>{comment.authorRole}</strong><span>{comment.body}</span></article>) : <p className="section-copy">No messages yet.</p>}<form className="form-grid" onSubmit={submitComment}><label className="wide">Add a message<textarea value={message} onChange={(event) => setMessage(event.target.value)} /></label><div className="wide"><button className="secondary-button" type="submit">Post message</button>{error ? <p className="form-message error">{error}</p> : null}</div></form></div></section>;
}
