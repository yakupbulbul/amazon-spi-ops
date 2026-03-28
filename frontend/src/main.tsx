import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { App } from "./App";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import "./index.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <PlaceholderPage title="Dashboard" /> },
      { path: "products", element: <PlaceholderPage title="Products" /> },
      { path: "aplus", element: <PlaceholderPage title="A+ Content Studio" /> },
      { path: "inventory", element: <PlaceholderPage title="Inventory" /> },
      { path: "notifications", element: <PlaceholderPage title="Notifications" /> },
      { path: "settings", element: <PlaceholderPage title="Settings" /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);

