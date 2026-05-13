import { useCallback, useEffect, useRef } from "react";

const NEAR_BOTTOM_THRESHOLD = 100;

/**
 * 自动滚底 hook：当内容变化时自动滚动到容器底部。
 * 如果用户主动向上滚动查看历史，自动滚底暂停；
 * 用户重新滚回底部后恢复。
 */
export function useAutoScroll(dependency: unknown) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const userScrolledUpRef = useRef(false);

  // 计算是否接近底部 (距离底部 < 100px)
  const isNearBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_THRESHOLD;
  }, []);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, []);

  // 监听用户手动滚动
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      if (isNearBottom()) {
        userScrolledUpRef.current = false;
      } else {
        userScrolledUpRef.current = true;
      }
    };

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [isNearBottom]);

  // 内容变化时自动滚底
  useEffect(() => {
    if (!userScrolledUpRef.current) {
      scrollToBottom();
    }
  }, [dependency, scrollToBottom]);

  return { containerRef, scrollToBottom };
}
