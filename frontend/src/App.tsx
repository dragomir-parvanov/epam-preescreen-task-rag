import { useState } from "react";
import type { components } from "./api/schema";
import { ArticlePanel } from "./article/ArticlePanel";
import { ChatPage } from "./chat/ChatPage";

type Passage = components["schemas"]["Passage"];

function App() {
  // The Passage whose Article is open in the panel, if any.
  const [opened, setOpened] = useState<Passage | null>(null);
  return (
    <>
      {/* Inert behind the open panel, so focus and screen readers stay in the panel. */}
      <div inert={opened !== null}>
        <ChatPage onOpenSection={setOpened} />
      </div>
      {opened && <ArticlePanel key={opened.id} passage={opened} onClose={() => setOpened(null)} />}
    </>
  );
}

export default App;
