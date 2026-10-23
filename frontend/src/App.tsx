import { ChatPage } from "./chat/ChatPage";

function App() {
  // Citation click-through opens the Article panel here (#32). Until then "Open Section" does nothing.
  return <ChatPage onOpenSection={() => undefined} />;
}

export default App;
