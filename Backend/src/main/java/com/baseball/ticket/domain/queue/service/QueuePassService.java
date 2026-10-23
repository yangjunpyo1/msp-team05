package com.baseball.ticket.domain.queue.service;

import com.baseball.ticket.global.exception.BusinessException;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

// 대기열 통과 기록 — queue:pass:{gameId}:{userId}
// 프론트가 좌석 화면 진입 시 대기열 토큰을 지우므로 통과 여부는 별도 키로 관리
@Service
@RequiredArgsConstructor
public class QueuePassService {

    private static final int PASS_TTL_MINUTES = 10;          // ALLOWED 후 좌석 선택 시간
    private static final int PASS_AFTER_LOCK_MINUTES = 10;   // 좌석 선점(5분) + 결제 여유 5분

    private final RedisTemplate<String, String> redisTemplate;

    private String key(String gameId, String userId) {
        return "queue:pass:" + gameId + ":" + userId;
    }

    // 대기열 ALLOWED 전환 시 발급
    public void grant(String gameId, String userId) {
        redisTemplate.opsForValue().set(key(gameId, userId), "1", PASS_TTL_MINUTES, TimeUnit.MINUTES);
    }

    // 좌석 선점·결제·예매 전 검사 (403은 CloudFront가 index.html로 바꾸므로 409 사용)
    public void require(String gameId, String userId) {
        if (!Boolean.TRUE.equals(redisTemplate.hasKey(key(gameId, userId)))) {
            throw new BusinessException("QUEUE_NOT_PASSED", 409);
        }
    }

    // 좌석 선점 성공 시 결제까지 만료되지 않도록 연장
    public void extendForPayment(String gameId, String userId) {
        redisTemplate.expire(key(gameId, userId), PASS_AFTER_LOCK_MINUTES, TimeUnit.MINUTES);
    }

    // 예매 확정 후 소진 (한 번 통과 = 한 번 예매)
    public void consume(String gameId, String userId) {
        redisTemplate.delete(key(gameId, userId));
    }
}
