# Signing and Notarizing the Mac App

**Quick reference (after one-time setup):**
```bash
# One-time: store notarization credentials
xcrun notarytool store-credentials "AC_PASSWORD" --apple-id "YOU@email.com" --team-id "TEAM_ID" --password "app-specific-password"

# Every release build (from repo root or electron/)
export CSC_NAME="Developer ID Application: Your Name (TEAM_ID)"
cd web-react && npm run build && cd ../electron && npm run build:mac && npm run dmg
```

---

## Where do I get the email and password?

You need **three** values for the one-time `notarytool store-credentials` command:

| Value | Where to get it |
|-------|------------------|
| **Email** | The **Apple ID email** you use to sign in to [developer.apple.com](https://developer.apple.com) (e.g. `you@gmail.com` or your iCloud address). Use that exact address in `--apple-id "YOU@email.com"`. |
| **Team ID** | In [developer.apple.com](https://developer.apple.com) → **Account** → **Membership** → look for **Team ID** (a 10-character string like `AB12CD34EF`). Or in Xcode: open any project → **Signing & Capabilities** → the **Team** dropdown shows it. Use it in `--team-id "TEAM_ID"`. |
| **Password** | **Not** your normal Apple ID password. You must create an **app-specific password**: 1. Go to [appleid.apple.com](https://appleid.apple.com) and sign in. 2. Open **Sign-In and Security** → **App-Specific Passwords**. 3. Click **Generate an app-specific password**, give it a name (e.g. “Notary” or “SpotifiMessage”), then **Create**. 4. Copy the **one-time** password (e.g. `xxxx-xxxx-xxxx-xxxx`) and paste it into `--password "..."`. You won’t be able to see it again; if you lose it, generate a new one. |

So in practice:

1. **Email** = Your Apple ID (same as developer.apple.com login).
2. **Team ID** = developer.apple.com → Account → Membership → Team ID.
3. **Password** = appleid.apple.com → Sign-In and Security → App-Specific Passwords → Generate → copy the generated password into `--password "..."`.

---

If users see **"SpotifiMessage.app is damaged and can't be opened"** (or "unidentified developer"), macOS Gatekeeper is blocking the app because it’s **unsigned** and **downloaded from the internet**. The app is not actually damaged.

## User workarounds (no Apple Developer account)

- **Right-click** the app → **Open** → click **Open** in the dialog.
- If that doesn’t work, in **Terminal**:  
  `xattr -dr com.apple.quarantine ~/Downloads/SpotifiMessage.app`  
  (or `/Applications/SpotifiMessage.app` if already in Applications.)

See the download page and release notes for the full text to give users.

---

## Long-term fix: Sign and notarize (Developer ID + notarytool)

Follow these steps once. After that, every release build can be signed and notarized so users don’t see Gatekeeper warnings.

### 1. Apple Developer account and certificate

1. **Enroll** at [developer.apple.com](https://developer.apple.com) ($99/year).
2. **Create a Developer ID Application certificate:**
   - Apple Developer → **Certificates, Identifiers & Profiles** → **Certificates** → **+**.
   - Choose **Developer ID Application** → continue → create a **Certificate Signing Request** on your Mac (Keychain Access → Certificate Assistant → Request a Certificate From a Certificate Authority → save to disk, then upload).
   - Download the certificate and double‑click to add it to **Keychain Access**.
3. **Note your Team ID:** Apple Developer → **Membership** → **Team ID** (or in Xcode: Signing & Capabilities → Team). You’ll use it for notarization.

### 2. App-specific password (for notarization)

1. Go to [appleid.apple.com](https://appleid.apple.com) → **Sign-In and Security** → **App-Specific Passwords**.
2. Generate a new app-specific password (e.g. name it “Notary”).
3. Copy it once; you’ll store it in the keychain in the next step.

### 3. Store notarization credentials in Keychain

Run this **once** on your Mac (replace placeholders):

```bash
xcrun notarytool store-credentials "AC_PASSWORD" \
  --apple-id "YOUR_APPLE_ID_EMAIL" \
  --team-id "YOUR_TEAM_ID" \
  --password "YOUR_APP_SPECIFIC_PASSWORD"
```

Use the **Team ID** from step 1 and the **app-specific password** from step 2. When prompted for “keychain item,” you can use the same name `AC_PASSWORD` or leave default. You should see: `Credentials validated.` and `Credentials saved to Keychain.`

### 4. Wire up code signing and notarization in the Electron app

Do this in **electron/** (or wherever your Electron `package.json` and build config live).

**4a. Install the notarize package**

```bash
cd electron
npm install @electron/notarize --save-dev
```

**4b. Configure code signing and afterSign**

In **electron/package.json**, ensure the `build` section has **mac** config with **hardenedRuntime** and **afterSign** pointing at the notarize script. Example:

```json
{
  "build": {
    "appId": "com.spotifimessage.app",
    "productName": "SpotifiMessage",
    "mac": {
      "category": "public.app-category.music",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "entitlements": "entitlements.mac.plist",
      "entitlementsInherit": "entitlements.mac.plist",
      "icon": "assets/icon.icns",
      "afterSign": "scripts/notarize.js"
    }
  }
}
```

**4c. Set code signing identity**

electron-builder will sign with your **Developer ID Application** certificate. Use one of:

- **Keychain identity (recommended)**  
  Export your Developer ID cert + private key, or use the identity already in Keychain. Set:
  ```bash
  export CSC_NAME="Developer ID Application: Your Name (TEAM_ID)"
  ```
  (Exact name as shown in Keychain.)

- **Or .p12 file**  
  Export the certificate as a .p12 from Keychain, then:
  ```bash
  export CSC_LINK="/path/to/DeveloperIDApplication.p12"
  export CSC_KEY_PASSWORD="p12_password"
  ```

**4d. Notarize script**

The repo includes **electron/scripts/notarize.js**, which uses `@electron/notarize` and:

- Reads **keychain profile** `AC_PASSWORD` (or the name you used in step 3), **or**
- Uses **APPLE_ID**, **APPLE_APP_SPECIFIC_PASSWORD**, and **APPLE_TEAM_ID** if you prefer not to use a keychain profile.

So either:

- Do nothing extra (script uses keychain profile `AC_PASSWORD`), **or**
- Set:
  ```bash
  export APPLE_KEYCHAIN_PROFILE="AC_PASSWORD"
  ```
  if you used a different profile name.

### 5. Build a signed and notarized release

From the **repo root** (or electron directory, depending on your scripts):

1. **Build with signing** (do **not** set `ELECTRON_BUILDER_UNSIGNED=1`):
   ```bash
   cd web-react && rm -rf build && npm run build && cd ..
   cd electron
   npm run build:mac
   ```
   Or, if you have a “signed” target that runs electron-builder without the unsigned flag, use that. electron-builder will:
   - Build the .app for each architecture (x64 and arm64).
   - Sign with your Developer ID (CSC_NAME or CSC_LINK).
   - Run **afterSign** → **scripts/notarize.js** for each .app, which submits to Apple and staples the notarization ticket.

2. **Create the DMG** from the **signed, notarized** .app(s):
   ```bash
   npm run dmg
   ```
   Use your existing DMG script; it should copy the already-signed/stapled app from `dist/mac` and `dist/mac-arm64` into the DMG. The resulting DMG does not need to be notarized again if it only contains the stapled app and symlinks; users can open the app without Gatekeeper blocking.

3. **Validate** (optional):
   ```bash
   xcrun stapler validate electron/dist/mac-arm64/SpotifiMessage.app
   ```

### 6. If you use a separate “unsigned” build

Keep your **unsigned** build for local testing:

- `ELECTRON_BUILDER_UNSIGNED=1 npm run build:mac` (or `build:mac:unsigned`) → no signing, no notarization.
- For **release**, run the same build **without** `ELECTRON_BUILDER_UNSIGNED` and with CSC_* and notary credentials set, so the same pipeline produces signed + notarized artifacts.

### Troubleshooting

- **“Invalid credentials”** – Use the app-specific password from appleid.apple.com, not your main Apple ID password. Re-run `notarytool store-credentials` and try again.
- **Signing fails (identity not found)** – Confirm `CSC_NAME` matches the certificate name in Keychain exactly, or that `CSC_LINK` points to a valid .p12 and `CSC_KEY_PASSWORD` is correct.
- **Notarization timeout** – Notarization can take several minutes. If it consistently times out, check [Apple’s notarization docs](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution) and ensure the app isn’t too large or missing entitlements.
- **Debug notarize script:**  
  `DEBUG=electron-notarize* npm run build:mac`

---

## Summary

| Step | What you do |
|------|-------------|
| 1 | Apple Developer account + Developer ID Application certificate in Keychain |
| 2 | App-specific password from appleid.apple.com |
| 3 | `xcrun notarytool store-credentials "AC_PASSWORD"` with Apple ID, team ID, app-specific password |
| 4 | In electron: install `@electron/notarize`, set `mac.afterSign: "scripts/notarize.js"`, set `CSC_NAME` (or `CSC_LINK` + `CSC_KEY_PASSWORD`) |
| 5 | Build **without** `ELECTRON_BUILDER_UNSIGNED`, then run your DMG script; distribute the DMG from the signed, notarized app |

After that, users can open the app from the DMG without Right‑click → Open or removing quarantine.
