import { FormEvent, useState } from "react";

import { authApi, User } from "../api";

type Props = { onAuthed: (token: string, user: User) => void };

export default function AuthPanel({ onAuthed }: Props) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState("");
  const submit = async (event: FormEvent) => { event.preventDefault(); try { const response = await authApi.login(email, password); onAuthed(response.token, response.user); } catch (nextError) { setError(nextError instanceof Error ? nextError.message : "Unable to sign in."); } };
  return <section className="section"><div className="panel"><p className="eyebrow">Admin</p><h2>Sign in</h2><form className="form-grid" onSubmit={submit}><label className="wide">Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="wide">Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><div className="wide"><button className="primary-button" type="submit">Sign in</button>{error ? <p className="form-message error">{error}</p> : null}</div></form></div></section>;
}
