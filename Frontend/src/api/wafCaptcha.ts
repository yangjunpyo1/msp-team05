// AWS WAF CAPTCHA / Challenge 공통 처리
// axios 응답 인터셉터에서 호출 — 화면과 무관하게 모든 API 요청에 적용

// CAPTCHA API 키는 kkybot 도메인용으로 WAF 콘솔/CLI에서 발급 — 빌드 시 환경변수로 주입
const WAF_CAPTCHA_API_KEY = import.meta.env.VITE_WAF_CAPTCHA_API_KEY ?? '';

declare global {
  interface Window {
    AwsWafCaptcha?: {
      renderCaptcha: (container: HTMLElement, options: {
        apiKey: string;
        onSuccess?: (wafToken: string) => void;
        onError?: (error: unknown) => void;
      }) => void;
    };
    AwsWafIntegration?: {
      fetch: (url: string, options?: RequestInit) => Promise<Response>;
      getToken?: () => Promise<string>;
    };
  }
}

// 동시에 여러 요청이 405를 받아도 모달은 하나만 띄움
let pendingCaptcha: Promise<void> | null = null;

export function showWafCaptcha(): Promise<void> {
  if (pendingCaptcha) return pendingCaptcha;

  pendingCaptcha = new Promise<void>((resolve, reject) => {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    overlay.innerHTML = `
      <div class="bg-white rounded-xl shadow-lg p-6 w-96">
        <h2 class="text-center font-bold text-lg mb-1">클린예매 서비스</h2>
        <p class="text-center text-sm text-gray-500 mb-4">
          부정예매를 방지하기 위해 <span class="text-blue-600 font-bold">보안 인증</span> 후 이용이 가능합니다.
        </p>
        <div data-captcha></div>
        <p data-error class="text-red-500 text-xs mt-2 text-center"></p>
        <button data-cancel class="w-full mt-4 py-2 border border-gray-300 rounded text-sm font-bold text-gray-600 hover:bg-gray-50">취소</button>
      </div>`;
    document.body.appendChild(overlay);

    const close = () => {
      overlay.remove();
      pendingCaptcha = null;
    };

    overlay.querySelector('[data-cancel]')!.addEventListener('click', () => {
      close();
      reject(new Error('WAF CAPTCHA cancelled'));
    });

    if (!window.AwsWafCaptcha) {
      overlay.querySelector('[data-error]')!.textContent = '보안 인증 모듈을 불러오지 못했습니다. 새로고침 해주세요.';
      return;
    }

    window.AwsWafCaptcha.renderCaptcha(overlay.querySelector('[data-captcha]') as HTMLElement, {
      apiKey: WAF_CAPTCHA_API_KEY,
      onSuccess: () => {
        close();
        resolve();
      },
      onError: (error) => {
        console.error('WAF CAPTCHA 에러', error);
        overlay.querySelector('[data-error]')!.textContent = '보안 인증 중 오류가 발생했습니다. 새로고침 해주세요.';
      },
    });
  });

  return pendingCaptcha;
}

// Challenge(202): SDK로 토큰(aws-waf-token 쿠키)을 발급받음
export async function solveWafChallenge(): Promise<void> {
  await window.AwsWafIntegration?.getToken?.();
}
