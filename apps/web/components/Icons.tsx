export function LoadingAnimation() {
    return (
        <svg
            width="14"
            height="14"
            viewBox="0 0 24 14"
            xmlns="http://www.w3.org/2000/svg"
        >
            <circle cx="4" cy="12" r="3">
                <animate
                    id="spinner_qFRN"
                    begin="0;spinner_OcgL.end+0.25s"
                    attributeName="cy"
                    calcMode="spline"
                    dur="0.6s"
                    values="12;6;12"
                    keySplines=".33,.66,.66,1;.33,0,.66,.33"
                />
            </circle>
            <circle cx="12" cy="12" r="3">
                <animate
                    begin="spinner_qFRN.begin+0.1s"
                    attributeName="cy"
                    calcMode="spline"
                    dur="0.6s"
                    values="12;6;12"
                    keySplines=".33,.66,.66,1;.33,0,.66,.33"
                />
            </circle>
            <circle cx="20" cy="12" r="3">
                <animate
                    id="spinner_OcgL"
                    begin="spinner_qFRN.begin+0.2s"
                    attributeName="cy"
                    calcMode="spline"
                    dur="0.6s"
                    values="12;6;12"
                    keySplines=".33,.66,.66,1;.33,0,.66,.33"
                />
            </circle>
        </svg>
    );
}

export function LoadingAnimation2() {
    return (
        <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
        >
            <style>{`
                .spinner_nOfF {
                    animation: spinner_qtyZ 2s cubic-bezier(0.36, 0.6, 0.31, 1) infinite;
                }
                .spinner_fVhf {
                    animation-delay: -0.5s;
                }
                .spinner_piVe {
                    animation-delay: -1s;
                }
                .spinner_MSNs {
                    animation-delay: -1.5s;
                }
                @keyframes spinner_qtyZ {
                    0% {
                        r: 0;
                    }
                    25% {
                        r: 3px;
                        cx: 4px;
                    }
                    50% {
                        r: 3px;
                        cx: 12px;
                    }
                    75% {
                        r: 3px;
                        cx: 20px;
                    }
                    100% {
                        r: 0;
                        cx: 20px;
                    }
                }
            `}</style>
            <circle className="spinner_nOfF" cx="4" cy="12" r="3" />
            <circle
                className="spinner_nOfF spinner_fVhf"
                cx="4"
                cy="12"
                r="3"
            />
            <circle
                className="spinner_nOfF spinner_piVe"
                cx="4"
                cy="12"
                r="3"
            />
            <circle
                className="spinner_nOfF spinner_MSNs"
                cx="4"
                cy="12"
                r="3"
            />
        </svg>
    );
}
