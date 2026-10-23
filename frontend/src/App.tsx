import { api } from "./api/client";

function App() {
  const { data, isError } = api.useQuery("get", "/health");
  const status = data?.status ?? (isError ? "unavailable" : "checking");

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-900">
      <p className="text-lg">
        Backend status: <span className="font-mono font-semibold">{status}</span>
      </p>
    </main>
  );
}

export default App;
