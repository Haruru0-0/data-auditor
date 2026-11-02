import { createRoot } from "react-dom/client";
import App, { parseAuditData } from "./App";
import "./styles.css";

const data = parseAuditData(document.getElementById("audit-data")?.textContent);
const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<App data={data} />);
}
