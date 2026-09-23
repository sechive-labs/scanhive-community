import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ size = 24, compact = false, children }: { size?: number; compact?: boolean; children: ReactNode }) {
  return (
    <div className={compact ? "loading-state compact" : "loading-state"}>
      <RefreshCw className="spin" size={size} />
      {children}
    </div>
  );
}
