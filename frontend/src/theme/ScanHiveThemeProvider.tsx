import { App as AntApp, ConfigProvider, theme as antTheme } from "antd";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type ThemeMode = "light" | "dark";
interface ThemeContextValue { mode: ThemeMode; toggle: () => void }
const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ScanHiveThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => localStorage.getItem("scanhive-theme") === "dark" ? "dark" : "light");

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
    localStorage.setItem("scanhive-theme", mode);
  }, [mode]);

  const value = useMemo(() => ({ mode, toggle: () => setMode((current) => current === "light" ? "dark" : "light") }), [mode]);

  return (
    <ThemeContext.Provider value={value}>
      <ConfigProvider theme={{
        algorithm: mode === "dark" ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        token: {
          colorPrimary: "#7c3aed", colorPrimaryHover: "#6d28d9", colorPrimaryActive: "#5b21b6", colorPrimaryBorder: "#7c3aed",
          colorSuccess: "#16a34a", colorWarning: "#d97706", colorError: "#dc2626", colorInfo: "#7c3aed",
          // Neutral (zinc) surfaces — violet is reserved for the primary accent only, never the base palette.
          colorBgBase: mode === "dark" ? "#09090b" : "#fafafa", colorBgContainer: mode === "dark" ? "#18181b" : "#ffffff",
          colorBgElevated: mode === "dark" ? "#27272a" : "#ffffff", colorText: mode === "dark" ? "#fafafa" : "#18181b",
          colorTextSecondary: mode === "dark" ? "#a1a1aa" : "#71717a", colorBorder: mode === "dark" ? "#3f3f46" : "#e4e4e7",
          colorBorderSecondary: mode === "dark" ? "#27272a" : "#f4f4f5", borderRadius: 6, controlHeight: 34, fontSize: 13,
          fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        },
        components: {
          Button: { primaryShadow: "none", fontWeight: 600 }, Card: { paddingLG: 20 },
          Table: { headerBg: mode === "dark" ? "#27272a" : "#f4f4f5", headerColor: mode === "dark" ? "#a1a1aa" : "#71717a", cellPaddingBlockSM: 9 },
          Menu: {
            itemHeight: 36, itemBorderRadius: 5,
            // The dark algorithm derives a selected-item text color too close to its own
            // selected-item background for this violet primary; pin a legible pair instead.
            ...(mode === "dark" ? { itemSelectedColor: "#e9d5ff", itemSelectedBg: "rgba(124, 58, 237, 0.28)" } : {}),
          },
          Pagination: {
            // Same low-contrast derivation issue as Menu's selected item, for the active page number.
            ...(mode === "dark" ? { itemActiveColor: "#e9d5ff", itemActiveBg: "rgba(124, 58, 237, 0.28)" } : {}),
          },
          Tabs: { horizontalItemPadding: "8px 0", titleFontSize: 13 },
        },
      }}><AntApp>{children}</AntApp></ConfigProvider>
    </ThemeContext.Provider>
  );
}

export function useScanHiveTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useScanHiveTheme must be used within ScanHiveThemeProvider");
  return context;
}
