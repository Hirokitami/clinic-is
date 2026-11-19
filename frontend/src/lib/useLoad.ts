"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

/** Загрузка данных с повторным запросом при изменении зависимостей. */
export function useLoad<T>(loader: () => Promise<T> | null, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  });
  const key = JSON.stringify(deps);

  const run = useCallback(() => {
    const id = ++seq.current;
    const p = loaderRef.current();
    if (!p) {
      Promise.resolve().then(() => {
        if (id !== seq.current) return;
        setData(null);
        setError(null);
        setLoading(false);
      });
      return;
    }
    Promise.resolve().then(() => id === seq.current && setLoading(true));
    p.then((d) => {
      if (id === seq.current) {
        setData(d);
        setError(null);
      }
    })
      .catch((e) => {
        if (id === seq.current) {
          setError(e instanceof ApiError ? e : new ApiError(0, { code: "ERROR", message: String(e) }));
          setData(null);
        }
      })
      .finally(() => {
        if (id === seq.current) setLoading(false);
      });
    // key – сериализованные зависимости вызывающего кода
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    run();
  }, [run]);

  return { data, error, loading, reload: run, setData };
}
