import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, Outlet, RouterProvider } from "react-router-dom";

import { App } from "./App";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { AplusStudioPage } from "./pages/AplusStudioPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InventoryPage } from "./pages/InventoryPage";
import { LoginPage } from "./pages/LoginPage";
import { ProductsPage } from "./pages/ProductsPage";
import { SectionPage } from "./pages/SectionPage";
import "./index.css";

const router = createBrowserRouter([
  {
    element: <Outlet />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: "/",
            element: <App />,
            children: [
              { index: true, element: <DashboardPage /> },
              {
                path: "products",
                element: <ProductsPage />,
              },
              {
                path: "aplus",
                element: <AplusStudioPage />,
              },
              {
                path: "inventory",
                element: <InventoryPage />,
              },
              {
                path: "notifications",
                element: (
                  <SectionPage
                    eyebrow="Delivery monitoring"
                    title="Notifications"
                    description="This area will track Slack dispatch history, event payloads, and message delivery outcomes across seller operations."
                    bullets={[
                      "Prepared for Slack webhook event logs and filters.",
                      "Prepared for publish, price, stock, and low-stock notification timelines.",
                    ]}
                  />
                ),
              },
              {
                path: "settings",
                element: (
                  <SectionPage
                    eyebrow="Configuration"
                    title="Settings"
                    description="Application settings, environment diagnostics, and outbound connection checks will live here."
                    bullets={[
                      "Reserved for webhook test actions and marketplace configuration.",
                      "Reserved for protected admin settings once auth scaffolding lands.",
                    ]}
                  />
                ),
              },
            ],
          },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </React.StrictMode>,
);
