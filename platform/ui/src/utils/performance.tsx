/**
 * Performance Monitoring Utilities
 *
 * Track and report performance metrics for the UI
 */

// React imports
import { useEffect, useCallback, useRef } from 'react';
import React from 'react';

interface PerformanceMetric {
  name: string;
  value: number;
  unit: string;
  timestamp: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private marks: Map<string, number> = new Map();

  /**
   * Start a performance measurement
   */
  mark(name: string): void {
    this.marks.set(name, performance.now());
    if (typeof performance.mark === 'function') {
      performance.mark(name);
    }
  }

  /**
   * End a performance measurement and record duration
   */
  measure(name: string, startMark: string): number {
    const startTime = this.marks.get(startMark);
    if (!startTime) {
      console.warn(`No start mark found for: ${startMark}`);
      return 0;
    }

    const duration = performance.now() - startTime;

    this.addMetric({
      name,
      value: duration,
      unit: 'ms',
      timestamp: Date.now(),
    });

    // Clear the mark
    this.marks.delete(startMark);

    return duration;
  }

  /**
   * Add a custom metric
   */
  addMetric(metric: PerformanceMetric): void {
    this.metrics.push(metric);

    // Keep only last 100 metrics
    if (this.metrics.length > 100) {
      this.metrics.shift();
    }
  }

  /**
   * Get all metrics
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get metrics by name
   */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter((m) => m.name === name);
  }

  /**
   * Get average value for a metric
   */
  getAverageMetric(name: string): number {
    const metrics = this.getMetricsByName(name);
    if (metrics.length === 0) return 0;

    const sum = metrics.reduce((acc, m) => acc + m.value, 0);
    return sum / metrics.length;
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
    this.marks.clear();
  }

  /**
   * Report Web Vitals
   */
  reportWebVitals(): void {
    if ('PerformanceObserver' in window) {
      // Largest Contentful Paint (LCP)
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1] as any;

        this.addMetric({
          name: 'LCP',
          value: lastEntry.renderTime || lastEntry.loadTime,
          unit: 'ms',
          timestamp: Date.now(),
        });
      });

      try {
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      } catch (e) {
        // LCP not supported
      }

      // First Input Delay (FID)
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          this.addMetric({
            name: 'FID',
            value: entry.processingStart - entry.startTime,
            unit: 'ms',
            timestamp: Date.now(),
          });
        });
      });

      try {
        fidObserver.observe({ entryTypes: ['first-input'] });
      } catch (e) {
        // FID not supported
      }

      // Cumulative Layout Shift (CLS)
      let clsValue = 0;
      const clsObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as any[]) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
            this.addMetric({
              name: 'CLS',
              value: clsValue,
              unit: 'score',
              timestamp: Date.now(),
            });
          }
        }
      });

      try {
        clsObserver.observe({ entryTypes: ['layout-shift'] });
      } catch (e) {
        // CLS not supported
      }
    }
  }

  /**
   * Get navigation timing metrics
   */
  getNavigationTiming(): Record<string, number> {
    const perfData = performance.getEntriesByType('navigation')[0] as any;
    if (!perfData) return {};

    return {
      'DNS Lookup': perfData.domainLookupEnd - perfData.domainLookupStart,
      'TCP Connection': perfData.connectEnd - perfData.connectStart,
      'Request Time': perfData.responseStart - perfData.requestStart,
      'Response Time': perfData.responseEnd - perfData.responseStart,
      'DOM Processing': perfData.domComplete - perfData.domLoading,
      'Load Complete': perfData.loadEventEnd - perfData.loadEventStart,
      'Total Load Time': perfData.loadEventEnd - perfData.fetchStart,
    };
  }

  /**
   * Log performance report to console
   */
  logReport(): void {
    console.group('Performance Report');

    // Web Vitals
    const lcp = this.getMetricsByName('LCP');
    const fid = this.getMetricsByName('FID');
    const cls = this.getMetricsByName('CLS');

    if (lcp.length > 0) {
      console.log(`LCP: ${lcp[lcp.length - 1].value.toFixed(2)}ms`);
    }
    if (fid.length > 0) {
      console.log(`FID: ${fid[fid.length - 1].value.toFixed(2)}ms`);
    }
    if (cls.length > 0) {
      console.log(`CLS: ${cls[cls.length - 1].value.toFixed(4)}`);
    }

    // Navigation timing
    const navTiming = this.getNavigationTiming();
    console.table(navTiming);

    // Custom metrics
    const customMetrics = this.metrics.filter(
      (m) => !['LCP', 'FID', 'CLS'].includes(m.name)
    );

    if (customMetrics.length > 0) {
      console.group('Custom Metrics');
      customMetrics.forEach((metric) => {
        console.log(`${metric.name}: ${metric.value.toFixed(2)}${metric.unit}`);
      });
      console.groupEnd();
    }

    console.groupEnd();
  }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitor();

/**
 * React hook for performance monitoring
 */
export function usePerformanceMonitor(metricName: string): {
  start: () => void;
  end: () => number;
} {
  const startMarkRef = useRef<string>('');

  const start = useCallback(() => {
    const markName = `${metricName}-${Date.now()}`;
    startMarkRef.current = markName;
    performanceMonitor.mark(markName);
  }, [metricName]);

  const end = useCallback(() => {
    if (!startMarkRef.current) {
      console.warn(`No start mark for: ${metricName}`);
      return 0;
    }

    const duration = performanceMonitor.measure(metricName, startMarkRef.current);
    startMarkRef.current = '';
    return duration;
  }, [metricName]);

  return { start, end };
}

/**
 * Component render time tracker
 */
export function withPerformanceTracking<P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
): React.ComponentType<P> {
  return (props: P) => {
    const { start, end } = usePerformanceMonitor(`render-${componentName}`);

    useEffect(() => {
      start();
      return () => {
        const duration = end();
        if (duration > 16) {
          // Longer than one frame (16ms at 60fps)
          console.warn(
            `Slow render detected in ${componentName}: ${duration.toFixed(2)}ms`
          );
        }
      };
    });

    return <Component {...props} />;
  };
}

/**
 * Measure async operation performance
 */
export async function measureAsync<T>(
  name: string,
  operation: () => Promise<T>
): Promise<T> {
  const startMark = `${name}-${Date.now()}`;
  performanceMonitor.mark(startMark);

  try {
    const result = await operation();
    performanceMonitor.measure(name, startMark);
    return result;
  } catch (error) {
    performanceMonitor.measure(`${name}-error`, startMark);
    throw error;
  }
}

/**
 * Bundle size reporter
 */
export function reportBundleSize(): void {
  if (typeof performance.getEntriesByType === 'function') {
    const resources = performance.getEntriesByType('resource') as any[];

    const jsResources = resources.filter((r) =>
      r.name.endsWith('.js') || r.name.includes('.js?')
    );

    const totalSize = jsResources.reduce(
      (acc, r) => acc + (r.encodedBodySize || 0),
      0
    );

    console.group('Bundle Size Report');
    console.log(`Total JS: ${(totalSize / 1024).toFixed(2)} KB`);
    console.log(`Number of JS files: ${jsResources.length}`);

    const largeFiles = jsResources
      .filter((r) => r.encodedBodySize > 100 * 1024) // > 100KB
      .sort((a, b) => b.encodedBodySize - a.encodedBodySize);

    if (largeFiles.length > 0) {
      console.warn('Large JS files (>100KB):');
      largeFiles.forEach((r) => {
        console.log(
          `  ${r.name.split('/').pop()}: ${(r.encodedBodySize / 1024).toFixed(2)} KB`
        );
      });
    }

    console.groupEnd();
  }
}

// Auto-initialize Web Vitals reporting
if (typeof window !== 'undefined') {
  performanceMonitor.reportWebVitals();

  // Log report on page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      performanceMonitor.logReport();
      reportBundleSize();
    }, 2000);
  });
}
