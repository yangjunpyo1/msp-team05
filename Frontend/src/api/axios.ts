import axios from 'axios';
import { showWafCaptcha, solveWafChallenge } from './wafCaptcha';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://kkybot.click',
  headers: {
    'Content-Type': 'application/json',
    //'Cache-Control': 'no-cache',
    //'Pragma': 'no-cache',
  },
});

// 요청 인터셉터 - JWT 토큰 자동 추가
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 응답 인터셉터 - WAF CAPTCHA/Challenge 처리, 토큰 만료 시 자동 갱신
api.interceptors.response.use(
  async (response) => {
    // WAF Challenge(202): 토큰 발급 후 원래 요청 1회 재시도
    if (response.status === 202
        && response.headers['x-amzn-waf-action'] === 'challenge'
        && !(response.config as any)._wafRetry) {
      (response.config as any)._wafRetry = true;
      await solveWafChallenge();
      return api(response.config);
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // WAF CAPTCHA(405): 캡차 모달을 풀면 원래 요청 1회 재시도
    if (error.response?.status === 405
        && error.response.headers['x-amzn-waf-action'] === 'captcha'
        && !originalRequest._wafRetry) {
      originalRequest._wafRetry = true;
      await showWafCaptcha();
      return api(originalRequest);
    }

    // 401 에러이고 재시도 안 한 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        // 토큰 갱신 요청
        const res = await axios.post(
          `${import.meta.env.VITE_API_URL || 'http://localhost:8080'}/api/auth/refresh`,
          {},
          { headers: { Authorization: `Bearer ${refreshToken}` } }
        );

        const newAccessToken = res.data.data.accessToken;
        localStorage.setItem('accessToken', newAccessToken);

        // 원래 요청 재시도
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // 갱신 실패 시 로그아웃
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;