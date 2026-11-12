import AdminDashboard from "@/components/AdminDashboard";

// Admin-only page. The link is shown only to ADMIN users; the backend also enforces the role (403).
export default function AdminPage() {
  return <AdminDashboard />;
}
