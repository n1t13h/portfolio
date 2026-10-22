import { useId, type ReactNode } from "react";

/**
 * Tiles for the developer intro: small designed cards (not brand logos) that scale to whatever
 * box they're dropped into. Content stays inside x 26-174, y 22-128 of the 200x150 viewBox because
 * `slice` crops the edges differently for each tile shape.
 */
// letterSpacing is reset on every tile: inside the wordmark window it would otherwise inherit the
// wordmark's tight tracking (-.05em of its huge font size) and squash the text.
const MONO = "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace";

function Card({
  label,
  bg,
  ink,
  children,
}: {
  label: string;
  bg: string;
  ink: string;
  children: ReactNode;
}) {
  return (
    <svg
      viewBox="0 0 200 150"
      preserveAspectRatio="xMidYMid slice"
      className="block h-full w-full"
      role="img"
      aria-label={label}
      fontFamily={MONO}
      letterSpacing="0"
    >
      <rect width="200" height="150" fill={bg} />
      <text x="26" y="32" fontSize="10" letterSpacing=".5" fill={ink} opacity=".9">
        {label}
      </text>
      {children}
    </svg>
  );
}

const Code = ({ lines, y = 62 }: { lines: ReactNode[][]; y?: number }) => (
  <>
    {lines.map((parts, i) => (
      <text key={i} x="26" y={y + i * 20} fontSize="10" style={{ whiteSpace: "pre" }}>
        {parts}
      </text>
    ))}
  </>
);
const T = ({ c, children }: { c: string; children: ReactNode }) => <tspan fill={c}>{children}</tspan>;

export const TemporalTile = () => (
  <Card label="temporal" bg="#0f1020" ink="#9aa0ff">
    <line x1="34" y1="88" x2="166" y2="88" stroke="#3b3f7a" strokeWidth="2" />
    <path d="M78 81 Q100 44 122 81" fill="none" stroke="#ff6aa8" strokeWidth="2" strokeDasharray="4 3" />
    {[34, 78, 122].map((x) => (
      <circle key={x} cx={x} cy="88" r="7" fill="#7c83ff" />
    ))}
    <circle cx="166" cy="88" r="7" fill="#1fbf5f" />
    {[
      [34, "start"],
      [78, "act"],
      [122, "retry"],
      [166, "done"],
    ].map(([x, t]) => (
      <text key={t} x={x as number} y="112" fontSize="8" textAnchor="middle" fill="#8a8fd0">
        {t}
      </text>
    ))}
  </Card>
);

export const AgenticAiTile = () => (
  <Card label="agentic ai" bg="#f1f1f0" ink="#0b0b0b">
    <rect x="40" y="40" width="110" height="26" rx="9" fill="#0b0b0b" />
    <text x="50" y="57" fontSize="10" fill="#fff">
      plan the trip
    </text>
    <rect x="30" y="74" width="132" height="48" rx="9" fill="#fff" />
    <text x="40" y="91" fontSize="9" fill="#333">
      3 sources, 1 answer
    </text>
    <rect x="40" y="99" width="30" height="14" rx="7" fill="#eef0ff" />
    <text x="55" y="109" fontSize="8" textAnchor="middle" fill="#3442ff">
      plan
    </text>
    <rect x="76" y="99" width="48" height="14" rx="7" fill="#eef0ff" />
    <text x="100" y="109" fontSize="8" textAnchor="middle" fill="#3442ff">
      retrieve
    </text>
    <rect x="130" y="99" width="22" height="14" rx="7" fill="#e5f8ec" />
    <text x="141" y="109" fontSize="8" textAnchor="middle" fill="#11934a">
      ✓
    </text>
  </Card>
);

export const Web3Tile = () => {
  const g = useId();
  return (
    <svg
      viewBox="0 0 200 150"
      preserveAspectRatio="xMidYMid slice"
      className="block h-full w-full"
      role="img"
      aria-label="web3"
      fontFamily={MONO}
      letterSpacing="0"
    >
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6d2bff" />
          <stop offset=".6" stopColor="#2b3bff" />
          <stop offset="1" stopColor="#00c2ff" />
        </linearGradient>
      </defs>
      <rect width="200" height="150" fill={`url(#${g})`} />
      <text x="26" y="32" fontSize="10" letterSpacing=".5" fill="#fff" opacity=".9">
        web3
      </text>
      <line x1="68" y1="82" x2="81" y2="82" stroke="#fff" strokeWidth="2" />
      <line x1="119" y1="82" x2="132" y2="82" stroke="#fff" strokeWidth="2" />
      {[
        [30, "0x7f"],
        [81, "0xa1"],
        [132, "0x3c"],
      ].map(([x, t]) => (
        <g key={t}>
          <rect x={x as number} y="62" width="38" height="40" rx="8" fill="#fff" fillOpacity=".16" stroke="#fff" />
          <text x={(x as number) + 19} y="86" fontSize="9" textAnchor="middle" fill="#fff">
            {t}
          </text>
        </g>
      ))}
    </svg>
  );
};

export const PythonTile = () => (
  <Card label="python" bg="#1d1f27" ink="#ffd43b">
    <Code
      lines={[
        [<T key="a" c="#c792ea">async def </T>, <T key="b" c="#82aaff">run</T>, <T key="c" c="#d6deeb">(job):</T>],
        [<T key="a" c="#d6deeb">{"  "}plan = </T>, <T key="b" c="#c792ea">await </T>, <T key="c" c="#d6deeb">agent(job)</T>],
        [<T key="a" c="#c792ea">{"  "}return </T>, <T key="b" c="#82aaff">verify</T>, <T key="c" c="#d6deeb">(plan)</T>],
      ]}
    />
  </Card>
);

export const MicroservicesTile = () => (
  <Card label="microservices" bg="#e9f7ef" ink="#0b6b3a">
    {[
      [48, 55],
      [152, 55],
      [48, 109],
      [152, 109],
    ].map(([x, y]) => (
      <line key={`${x}-${y}`} x1="100" y1="82" x2={x} y2={y} stroke="#0b0b0b" strokeWidth="1.2" />
    ))}
    <rect x="80" y="70" width="40" height="24" rx="5" fill="#0b0b0b" />
    <text x="100" y="86" fontSize="9" textAnchor="middle" fill="#fff">
      api
    </text>
    {[
      [28, 44, "auth"],
      [132, 44, "orders"],
      [28, 98, "pay"],
      [132, 98, "ai"],
    ].map(([x, y, t]) => (
      <g key={t}>
        <rect x={x as number} y={y as number} width="40" height="22" rx="5" fill="#fff" stroke="#0b0b0b" />
        <text x={(x as number) + 20} y={(y as number) + 14} fontSize="8" textAnchor="middle" fill="#0b0b0b">
          {t}
        </text>
      </g>
    ))}
  </Card>
);

export const TypeScriptTile = () => (
  <Card label="typescript" bg="#e8f0ff" ink="#1f4fb4">
    <Code
      lines={[
        [<T key="a" c="#7a3cc4">type </T>, <T key="b" c="#1f4fb4">Job</T>, <T key="c" c="#333"> = {"{"}</T>],
        [<T key="a" c="#333">{"  "}id: </T>, <T key="b" c="#0b7a4b">string</T>],
        [<T key="a" c="#333">{"  "}status: </T>, <T key="b" c="#b4541f">"done"</T>],
        [<T key="a" c="#333">{"}"}</T>],
      ]}
      y={56}
    />
  </Card>
);

export const ServerlessTile = () => (
  <Card label="serverless" bg="#ff8a1f" ink="#fff">
    <text x="100" y="112" fontSize="72" textAnchor="middle" fill="#fff" fontFamily="Georgia, serif">
      λ
    </text>
  </Card>
);

export const PostgresTile = () => (
  <Card label="postgres" bg="#eef3ff" ink="#1f4fb4">
    <rect x="34" y="44" width="132" height="80" rx="6" fill="#fff" stroke="#cfd8f5" />
    <rect x="34" y="44" width="132" height="18" rx="6" fill="#dbe4ff" />
    <text x="44" y="56" fontSize="8" fill="#1f4fb4">
      id
    </text>
    <text x="84" y="56" fontSize="8" fill="#1f4fb4">
      status
    </text>
    {[
      ["41", "queued"],
      ["42", "running"],
      ["43", "done"],
    ].map(([id, st], i) => (
      <g key={id}>
        <text x="44" y={80 + i * 18} fontSize="8" fill="#333">
          {id}
        </text>
        <text x="84" y={80 + i * 18} fontSize="8" fill={st === "done" ? "#11934a" : "#333"}>
          {st}
        </text>
      </g>
    ))}
  </Card>
);

export const SolidityTile = () => (
  <Card label="solidity" bg="#17141f" ink="#b9a2ff">
    <Code
      lines={[
        [<T key="a" c="#c792ea">function </T>, <T key="b" c="#82aaff">stake</T>, <T key="c" c="#d6deeb">()</T>],
        [<T key="a" c="#d6deeb">{"  "}external </T>, <T key="b" c="#c792ea">payable</T>],
        [<T key="a" c="#d6deeb">{"  "}{"{"} mint(msg.value); {"}"}</T>],
      ]}
    />
  </Card>
);
