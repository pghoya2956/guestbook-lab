// 오늘 급식 화면에 꼭 필요한 동작 두 가지. 이 파일이 없어도 리뷰 쓰기와 보기는 된다.

// 1. 운영 띠의 /health 를 30초마다 불러 응답 코드와 걸린 시간을 보인다
(function () {
  var el = document.querySelector("[data-health]");
  if (!el || !window.fetch) return;
  function check() {
    var start = performance.now();
    fetch("/health", { cache: "no-store" })
      .then(function (r) {
        // 휴대폰에서는 걸린 시간만 보인다(.ops-wide 를 CSS 가 숨긴다)
        el.innerHTML = '<span class="ops-wide">/health ' + r.status + ", </span>" + Math.round(performance.now() - start) + "ms";
        el.classList.toggle("is-down", !r.ok);
      })
      .catch(function () {
        el.textContent = "/health 응답 없음";
        el.classList.add("is-down");
      });
  }
  check();
  setInterval(check, 30000);
})();

// 2. 급식 사진을 고르면 단추에 고른 파일 이름을 보인다
(function () {
  var input = document.querySelector("[data-photo]");
  var text = document.querySelector("[data-photo-text]");
  if (!input || !text) return;
  input.addEventListener("change", function () {
    var f = input.files && input.files[0];
    text.textContent = f ? f.name : "급식 사진";
    input.parentNode.classList.toggle("has-file", !!f);
  });
})();
