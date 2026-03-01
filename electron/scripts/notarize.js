/**
 * Notarize the built Mac app (for use as electron-builder afterSign hook).
 *
 * Prerequisites:
 * - Apple Developer account, Developer ID Application certificate in Keychain
 * - Notarization credentials stored in Keychain:
 *     xcrun notarytool store-credentials "AC_PASSWORD"
 *       --apple-id "your@email.com"
 *       --team-id "TEAM_ID"
 *       --password "app-specific-password"
 *
 * Environment:
 * - APPLE_KEYCHAIN_PROFILE (default: "AC_PASSWORD") — keychain profile from notarytool store-credentials
 *   OR for app-specific password without keychain profile:
 * - APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID
 *
 * Usage in electron/package.json build.mac.afterSign:
 *   "afterSign": "scripts/notarize.js"
 */
const { notarize } = require('@electron/notarize');
const path = require('path');

module.exports = async function afterSign(context) {
  const { appOutDir } = context;
  const productFilename = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${productFilename}.app`);

  const keychainProfile = process.env.APPLE_KEYCHAIN_PROFILE || 'AC_PASSWORD';
  const appleId = process.env.APPLE_ID;
  const appleIdPassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  const opts = { appPath: path.resolve(appPath) };

  if (appleId && appleIdPassword && teamId) {
    opts.appleId = appleId;
    opts.appleIdPassword = appleIdPassword;
    opts.teamId = teamId;
  } else {
    opts.keychainProfile = keychainProfile;
  }

  console.log('Notarizing', appPath, '...');
  await notarize(opts);
  console.log('Notarization complete.');
};
