import React from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "jotai";
import { BrowserRouter } from "react-router";
import App from "./App";
import "./index.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Provider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>,
);
