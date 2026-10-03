import { Suspense, lazy } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router";
import { Sparkles, Workflow, Film } from "lucide-react";
const Pipeline = lazy(() => import("./pages/Pipeline"));
const MotionEditor = lazy(() => import("./pages/MotionEditor"));
export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/pipeline" className="brand">
          <Sparkles size={22} /> Motion Studio <span>角色动画工具库</span>
        </Link>
        <nav>
          <NavLink to="/pipeline">
            <Workflow size={16} /> 制作流水线
          </NavLink>
          <NavLink to="/motion">
            <Film size={16} /> 动作工作层
          </NavLink>
        </nav>
      </header>
      <main>
        <Suspense fallback={<p role="status">正在加载工作区…</p>}>
          <Routes>
            <Route path="/pipeline/:step?" element={<Pipeline />} />
            <Route path="/motion" element={<MotionEditor />} />
            {/* 保留旧书签，统一进入React路由，不再运行旧HTML页面。 */}
            <Route
              path="/toolkit.html"
              element={<Navigate to="/pipeline" replace />}
            />
            <Route
              path="/engine-pilot/*"
              element={<Navigate to="/motion" replace />}
            />
            <Route path="/" element={<Navigate to="/pipeline" replace />} />
            <Route
              path="*"
              element={
                <div>
                  <h1>页面不存在</h1>
                  <Link to="/pipeline">返回制作流水线</Link>
                </div>
              }
            />
          </Routes>
        </Suspense>
      </main>
      <footer>原画保持冻结 · 时序精确到毫秒 · 生图与验收分别记录</footer>
    </div>
  );
}
