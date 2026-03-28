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
import { NotificationsPage } from "./pages/NotificationsPage";
import { ProductsPage } from "./pages/ProductsPage";
import { SettingsPage } from "./pages/SettingsPage";
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
                element: <NotificationsPage />,
              },
              {
                path: "settings",
                element: <SettingsPage />,
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
