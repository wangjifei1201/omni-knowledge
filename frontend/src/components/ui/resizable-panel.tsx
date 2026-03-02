"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

interface ResizablePanelProps {
  children: React.ReactNode;
  className?: string;
  defaultSize?: number;
  minSize?: number;
  maxSize?: number;
  side: "left" | "right";
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function ResizablePanel({
  children,
  className,
  defaultSize = 320,
  minSize = 200,
  maxSize = 600,
  side,
  collapsed = false,
  onCollapsedChange: _onCollapsedChange,
}: ResizablePanelProps) {
  const [size, setSize] = useState(defaultSize);
  const [isDragging, setIsDragging] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!panelRef.current) return;

      let newSize: number;
      if (side === "left") {
        const rect = panelRef.current.getBoundingClientRect();
        newSize = e.clientX - rect.left;
      } else {
        const rect = panelRef.current.getBoundingClientRect();
        newSize = rect.right - e.clientX;
      }

      newSize = Math.max(minSize, Math.min(maxSize, newSize));
      setSize(newSize);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, minSize, maxSize, side]);

  if (collapsed) {
    return null;
  }

  return (
    <div
      ref={panelRef}
      className={cn("relative flex-shrink-0", className)}
      style={{ width: size }}
    >
      {children}
      {/* 拖拽手柄 */}
      <div
        className={cn(
          "absolute top-0 bottom-0 w-1 cursor-col-resize z-10 group",
          "hover:bg-primary/30 transition-colors",
          isDragging && "bg-primary/50",
          side === "left" ? "right-0" : "left-0"
        )}
        onMouseDown={handleMouseDown}
      >
        <div
          className={cn(
            "absolute top-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-border",
            "group-hover:bg-primary/50 transition-colors",
            isDragging && "bg-primary",
            side === "left" ? "right-0" : "left-0"
          )}
        />
      </div>
    </div>
  );
}
