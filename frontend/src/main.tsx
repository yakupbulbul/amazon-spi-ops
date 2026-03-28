import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, Outlet, RouterProvider } from "react-router-dom";

import { App } from "./App";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { DashboardPage } from "./pages/DashboardPage";
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
                element: (
                  <SectionPage
                    eyebrow="Creative workflow"
                    title="A+ Content Studio"
                    description="This route is reserved for structured AI draft generation, editable previews, and Amazon-compatible payload mapping."
                    bullets={[
                      "Ready for prompt inputs such as brand tone and positioning.",
                      "Ready for structured JSON validation and draft preview panels.",
                    ]}
                  />
                ),
              },
              {
                path: "inventory",
                element: (
                  <SectionPage
                    eyebrow="Inventory operations"
                    title="Inventory"
                    description="This screen will become the monitoring surface for stock levels, low-stock alerts, sync jobs, and manual refresh actions."
                    bullets={[
                      "Reserved for SKU, ASIN, quantity, and health badge tables.",
                      "Reserved for low-stock threshold alerts and scheduled sync visibility.",
                    ]}
                  />
                ),
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
