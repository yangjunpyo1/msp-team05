# React + TypeScript + Vite

## 배포 환경변수 (KKYBot)

빌드 전에 `.env.example`을 `.env.production`으로 복사해 값을 채운다. `.env*` 파일은 커밋하지 않는다.

| 변수 | 용도 |
|---|---|
| `VITE_API_URL` | 백엔드 API 주소 (예: `https://kkybot.net`) |
| `VITE_WAF_CAPTCHA_SDK_URL` | AWS WAF CAPTCHA SDK(`jsapi.js`) 주소 — `index.html`에서 로드 |
| `VITE_WAF_CHALLENGE_SDK_URL` | AWS WAF Challenge SDK(`challenge.js`) 주소 — `index.html`에서 로드 |
| `VITE_WAF_CAPTCHA_API_KEY` | CAPTCHA 위젯 API 키 (서비스 도메인용으로 발급) |

SDK 주소와 API 키는 Web ACL을 다시 만들면 바뀌므로, 인프라 재생성 후 `.env.example`의 CLI 명령으로 다시 조회한다.
WAF가 CAPTCHA(405)나 Challenge(202)를 응답하면 `src/api/axios.ts` 인터셉터가 공통으로 처리한다(`src/api/wafCaptcha.ts`).

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
