type Status = { state: string; detail: string };
type WhisprBridge = { toggle: () => void; onStatus: (callback: (status: Status) => void) => void };
declare global { interface Window { whispr: WhisprBridge } }
export {};

const pill = document.querySelector<HTMLElement>("#pill")!;
const label = document.querySelector<HTMLElement>("#label")!;
const hint = document.querySelector<HTMLElement>("#hint")!;
const meter = document.querySelector<HTMLElement>("#meter")!;

window.whispr.onStatus(({ state, detail }) => {
  pill.dataset.state = state;
  label.textContent = detail;
  hint.textContent = state === "listening" ? "release" : state === "transcribing" ? "working" : state === "error" ? "retry" : "hold space";
  meter.classList.toggle("active", state === "listening");
});

pill.addEventListener("click", () => window.whispr.toggle());
