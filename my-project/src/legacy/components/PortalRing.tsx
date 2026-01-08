/**
 * PortalRing Component
 *
 * The portal ring overlay and inner shadow.
 */

export function PortalRing() {
  return (
    <>
      {/* Portal ring image */}
      <div
        style={{
          position: 'absolute',
          left: '20px',
          right: '20px',
          top: '0px',
          bottom: '0px',
          backgroundImage: 'url("/assets/images/portal-ring.webp")',
          backgroundSize: 'contain',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          zIndex: 30,
          pointerEvents: 'none',
          filter:
            'drop-shadow(0 6px 4px rgba(0,0,0,0.5)) drop-shadow(0 12px 10px rgba(0,0,0,0.4)) drop-shadow(0 24px 20px rgba(0,0,0,0.3)) drop-shadow(0 40px 35px rgba(0,0,0,0.2)) drop-shadow(0 60px 50px rgba(0,0,0,0.15))',
        }}
      />

      {/* Inner shadow at bottom of portal ring interior */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: 'calc(min(100%, 100vh - 40px) * 0.68)',
          height: 'calc(min(100%, 100vh - 40px) * 0.68)',
          borderRadius: '50%',
          boxShadow:
            'inset 0 -62px 50px -14px rgba(0,0,0,0.84), inset 0 -103px 72px -29px rgba(0,0,0,0.62), inset 0 -134px 91px -39px rgba(0,0,0,0.43)',
          zIndex: 29,
          pointerEvents: 'none',
        }}
      />
    </>
  );
}
