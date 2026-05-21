import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Chat } from "./pages/Chat";
import { History } from "./pages/History";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Chat },
      { path: "history", Component: History },
    ],
  },
]);
