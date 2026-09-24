type Props = { isAdmin: boolean; onHome: () => void; onRequest: () => void; onAdmin: () => void };

export default function Navigation({ isAdmin, onHome, onRequest, onAdmin }: Props) {
  return <nav className="nav" aria-label="Main navigation"><button className="brand" type="button" onClick={onHome}>DAVID</button><div className="nav-links"><button className="text-button" type="button" onClick={onHome}>Work</button><button className="text-button" type="button" onClick={onRequest}>Request a site</button><button className="text-button" type="button" onClick={onAdmin}>{isAdmin ? "Admin" : "Sign in"}</button></div></nav>;
}
