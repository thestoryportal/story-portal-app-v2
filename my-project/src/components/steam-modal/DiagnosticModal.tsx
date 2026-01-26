/**
 * Diagnostic version of Steam Modal to debug CSS module loading
 * This logs what classes are being applied to help diagnose issues
 */

import { useEffect } from 'react';
import styles from './SteamModal.module.css';
import backdropStyles from './Backdrop.module.css';
import headerStyles from './PanelHeader.module.css';
import steamStyles from './SteamField.module.css';
import contentStyles from './ContentPanel.module.css';

export function DiagnosticModal() {
  useEffect(() => {
    console.group('=== CSS Module Diagnostic ===');

    console.log('SteamModal styles:', styles);
    console.log('Backdrop styles:', backdropStyles);
    console.log('Header styles:', headerStyles);
    console.log('Steam styles:', steamStyles);
    console.log('Content styles:', contentStyles);

    console.log('\n--- Expected vs Actual ---');
    console.log('Backdrop class should be:', backdropStyles.backdrop || 'MISSING!');
    console.log('Header class should be:', headerStyles.header || 'MISSING!');
    console.log('Content class should be:', contentStyles.contentPanel || 'MISSING!');

    console.groupEnd();
  }, []);

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 10000,
      background: 'rgba(0,0,0,0.9)',
      color: 'white',
      padding: '40px',
      overflow: 'auto',
      fontFamily: 'monospace',
    }}>
      <h1>CSS Module Diagnostic</h1>
      <p>Check the browser console for detailed output.</p>

      <div style={{ marginTop: '20px', background: 'rgba(255,255,255,0.1)', padding: '20px', borderRadius: '8px' }}>
        <h2>Quick Visual Test:</h2>

        <div style={{ marginTop: '20px' }}>
          <h3>Backdrop Test:</h3>
          <div className={backdropStyles.backdrop} style={{
            position: 'relative',
            width: '200px',
            height: '100px',
            display: 'inline-block',
          }}>
            Backdrop (should have dark vignette)
          </div>
          <p>Class applied: <code>{backdropStyles.backdrop || 'NONE'}</code></p>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h3>Header Test:</h3>
          <div className={headerStyles.header} style={{
            position: 'relative',
            display: 'inline-block',
          }}>
            <div className={headerStyles.title}>
              Test Header
            </div>
          </div>
          <p>Class applied: <code>{headerStyles.header || 'NONE'}</code></p>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h3>Content Panel Test:</h3>
          <div className={contentStyles.contentPanel} style={{
            position: 'relative',
            display: 'inline-block',
            maxWidth: '400px',
          }}>
            <p className={contentStyles.bodyText}>
              This text should be dark brown on parchment background.
            </p>
          </div>
          <p>Class applied: <code>{contentStyles.contentPanel || 'NONE'}</code></p>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h3>Steam Field Test:</h3>
          <div className={steamStyles.steamField} style={{
            position: 'relative',
            width: '300px',
            height: '200px',
            background: '#1a1a1a',
          }}>
            <div className={steamStyles.radialBase}>Radial Base</div>
            <div className={steamStyles.radialMid}>Radial Mid</div>
          </div>
          <p>Classes applied: <code>{steamStyles.steamField || 'NONE'}</code></p>
        </div>
      </div>

      <div style={{ marginTop: '40px', background: 'rgba(255,255,255,0.1)', padding: '20px', borderRadius: '8px' }}>
        <h2>Instructions:</h2>
        <ol>
          <li>Check the browser console for the CSS module object dumps</li>
          <li>Look at the visual tests above - do they have the expected styling?</li>
          <li>If class names are MISSING or NONE, CSS modules aren't loading</li>
          <li>If class names are present but styles don't apply, there's a CSS conflict</li>
        </ol>
      </div>
    </div>
  );
}
