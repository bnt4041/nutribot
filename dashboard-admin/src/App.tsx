import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Documents from "./pages/Documents";
import Legal from "./pages/Legal";
import Login from "./pages/Login";
import Metrics from "./pages/Metrics";
import Users from "./pages/Users";

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
        <Route path="/" element={<Metrics />} />
        <Route path="/usuarios" element={<Users />} />
        <Route path="/documentos" element={<Documents />} />
        <Route path="/legal" element={<Legal />} />
      </Route>
    </Routes>
  );
}
