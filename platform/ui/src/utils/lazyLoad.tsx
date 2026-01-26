/**
 * Lazy Loading Utilities
 *
 * Provides enhanced lazy loading with error boundaries and loading states
 */

import { lazy, Suspense, ComponentType, ReactNode } from 'react';

interface LazyLoadOptions {
  fallback?: ReactNode;
  errorFallback?: ReactNode;
  delay?: number;
}

/**
 * Enhanced lazy loading with retry logic
 */
export function lazyWithRetry<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  options: LazyLoadOptions = {}
): ComponentType<any> {
  const { fallback = <LoadingSpinner />, delay = 0 } = options;

  const LazyComponent = lazy(() => {
    return new Promise<{ default: T }>((resolve, reject) => {
      const hasRefreshed = JSON.parse(
        sessionStorage.getItem('retry-lazy-refreshed') || 'false'
      );

      // Try importing the component
      importFunc()
        .then((component) => {
          sessionStorage.setItem('retry-lazy-refreshed', 'false');
          if (delay > 0) {
            setTimeout(() => resolve(component), delay);
          } else {
            resolve(component);
          }
        })
        .catch((error) => {
          if (!hasRefreshed) {
            // Retry once by refreshing the page
            sessionStorage.setItem('retry-lazy-refreshed', 'true');
            return window.location.reload();
          }
          // Already retried, reject
          reject(error);
        });
    });
  });

  return (props: any) => (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

/**
 * Preload a lazy component
 */
export function preloadComponent(
  importFunc: () => Promise<{ default: ComponentType<any> }>
): void {
  importFunc();
}

/**
 * Default loading spinner
 */
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>
  );
}

/**
 * Loading skeleton for lazy components
 */
export function LazyLoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-4 p-4">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded"></div>
      ))}
    </div>
  );
}

/**
 * Lazy load with custom loading component
 */
export function lazyWithFallback<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  fallback: ReactNode = <LoadingSpinner />
): ComponentType<any> {
  const LazyComponent = lazy(importFunc);

  return (props: any) => (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

/**
 * Lazy load only when in viewport (Intersection Observer)
 */
export function LazyLoadOnView({
  children,
  fallback = <LazyLoadingSkeleton />,
  rootMargin = '50px',
}: {
  children: ReactNode;
  fallback?: ReactNode;
  rootMargin?: string;
}) {
  const [isInView, setIsInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [rootMargin]);

  return <div ref={ref}>{isInView ? children : fallback}</div>;
}

// React imports for LazyLoadOnView
import { useState, useEffect, useRef } from 'react';
