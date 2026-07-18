import { useEffect, useState } from "react";
import { getHealth } from "./api/client";

type Status = { kind: "loading" } | { kind: "healthy" } | { kind: "error"; message: string };

function App() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    getHealth()
      .then(() => setStatus({ kind: "healthy" }))
      .catch((err) => setStatus({ kind: "error", message: String(err) }));
  }, []);

  return (
    <main>
      <h1>Expense Tracker</h1>
      {status.kind === "loading" && <p>Checking backend…</p>}
      {status.kind === "healthy" && <p>backend: healthy</p>}
      {status.kind === "error" && <p>backend: unreachable ({status.message})</p>}
    </main>
  );
}

export default App;
