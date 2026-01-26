import React from 'react';
import SteamComparisonTest from './components/steam-modal/enhanced/SteamComparisonTest';

/**
 * Test Page for Steam Animation v35 → v36 Comparison
 *
 * Usage:
 * 1. Import this component in your App.tsx or routing
 * 2. Navigate to the route where this component is rendered
 * 3. Use the controls to compare versions
 *
 * Or for quick testing, temporarily replace App.tsx content with:
 *
 * import TestSteamComparison from './TestSteamComparison';
 *
 * function App() {
 *   return <TestSteamComparison />;
 * }
 *
 * export default App;
 */
function TestSteamComparison() {
  return <SteamComparisonTest />;
}

export default TestSteamComparison;
