import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';

declare global {
  interface Window {
    AwsWafCaptcha: any;
  }
}

export default function VerifyPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const boxRef = useRef<HTMLDivElement>(null);
  const rendered = useRef(false);

  useEffect(() => {
    if (rendered.current) return;
    rendered.current = true;

    const renderWhenReady = () => {
      if (window.AwsWafCaptcha && boxRef.current) {
        window.AwsWafCaptcha.renderCaptcha(boxRef.current, {
          apiKey: 'EmiTvaZ8WwCGxbGLHpwxfsYqBtONuYY4w/tBpnC14Ow2Ub8qcMI4KMoHz7zrD6imuLRruR2BgBzLRIJk0CVq746eUTVYYTdvzG/i2S4N6IQlmKg3ujhX+sub6DOOhp7w7iEcNvEOdlcyD1G3XmrJ0QFTqykMfwH/jeNpFog6hrW241HfC/vrWG2vu3qxUcv7FsbxdVFD7RCehif5He+IN5rx2MHuOsc0TFj4C/WNkwbxH9vcbTUfPW8MnlKRvbbo7b5tSwUOFxv3JVihlXQjecZOkq04mNUeR5+Vu46bgB6azS4TqZYQ0587zGHCHMXk/1d1B70ReuHM+w2F58MHsvJ5+7+pBVHPSP1oxFHpkRJ8C9S4bYwuGhwjsm/x9BCIqBz7PcbaT3qNizs9sQ/t+czf4u08nhbNc+0OqzFVxA3zeeTvgoUPGX6IEfECTIzzUYjLWv/OsLZ7wtNlVVZXZJ/8AEqeokXWgfxL/8Ts+0bN9VmQKfyBvZrCMV1E+pz3+nZeYbkTbjPuB5e0UlPuVL0O7o7Yx0G0t7XqFygKlAjHMuRu+J7xRKo/fL6UYnDPJoKtj5Tceq2ggV73SvJXj0Z5fiVXwmnlCwSrH2v3aWi3Ba4xyiGcR1CuhssjwjP+wCrARJFdACBj2uLKiL5esn541FeDwmYyHHjrKwTNe7k=_1_1',
          onSuccess: function () {
            navigate(`/games/${gameId}/seats`);
          },
          onError: function () {
            // 에러시 그대로 머무름 (재시도 가능)
          },
        });
      } else {
        setTimeout(renderWhenReady, 200);
      }
    };

    renderWhenReady();
  }, [gameId, navigate]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-md mx-auto px-4 py-16 text-center">
        <div className="bg-white rounded-xl shadow p-8">
          <h1 className="text-xl font-bold text-blue-900 mb-2">보안 확인이 필요합니다</h1>
          <p className="text-gray-500 mb-6 text-sm">
            비정상적인 접근이 감지되어 본인 확인을 진행합니다.
          </p>
          <div ref={boxRef} className="min-h-[280px] flex items-center justify-center" />
        </div>
      </div>
    </div>
  );
}
