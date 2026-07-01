import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Conversations from "./pages/Conversations";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Progress from "./pages/Progress";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Progress />} />
        <Route path="/perfil" element={<Profile />} />
        <Route path="/conversaciones" element={<Conversations />} />
      </Route>
    </Routes>
  );
}
