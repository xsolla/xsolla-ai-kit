// Reference: a whole webshop page as ONE Shop Builder custom block.
//
// A worked companion to skills/buy-button/references/buy-button-block.tsx: that one
// embeds a single widget, this one shows what a full page looks like when the design
// (header, hero, store grid, FAQ, CTA, footer, purchase modal) lives inside a single
// federated block, plus a real Xsolla Login integration.
//
// Publish it with:
//   xsolla shopbuilder create-custom-block \
//     --landing-id <top-level _id from get-structure> \
//     --page-id    <page _id from get-structure> \
//     --name "My Shop" \
//     --component-code "$(cat webshop-custom-block.tsx)"
//
// Fill these in before publishing (all are placeholders here on purpose):
//   * CDN + the YOUR_*_ASSET.png names — upload your art with
//     `xsolla shopbuilder upload-asset --landing-id <L> --file art.png --type image`
//     and paste the returned .data.url values.
//   * LOGIN_PROJECT_ID — the landing's own Login project: read `auth.loginId` from
//     `xsolla shopbuilder get-structure --slug <slug> --json`. Site Builder registers
//     the site's domain on that project automatically, so the widget's callback origin
//     is normally already allow-listed.
//
// Notes learned the hard way:
//   * ONE block, not several — blocks are separate federated remotes and cannot share
//     React state, so anything with a shared cart/modal/session belongs in one block.
//   * The compiled bundle is served with `cache-control: max-age=14400`. Updating a
//     block in place keeps its URL, so browsers hold the old bundle; when you need a
//     change visible immediately, delete the block and create a new one to get a new URL.
//   * Prefer native Site Builder blocks (`newStore`) and native auth when you do not
//     need pixel-exact control — this file is the escape hatch, not the default.

import React, { useEffect, useRef, useState } from "react";

/* ---------------------------------------------------------------- theme */

const CTA = "#6C2BD9";
const CTA_SHADOW = "#3F1585";
const SHOW_FREE_GIFT = true;

/* ---------------------------------------------------------------- assets */

const CDN =
	"https://cdn.xsolla.net/merchant-bucket-prod/files/uploaded/sitebuilder/YOUR_MERCHANT_ID/";
const KEYART = CDN + "YOUR_KEYART_ASSET.png";
const DUFFEL = CDN + "YOUR_DUFFEL_ASSET.png";
const PURSE = CDN + "YOUR_PURSE_ASSET.png";
const TRIO = CDN + "YOUR_TRIO_ASSET.png";
const STACK = CDN + "YOUR_STACK_ASSET.png";
const SACK = CDN + "YOUR_SACK_ASSET.png";
const LOCK = CDN + "YOUR_LOCK_ASSET.png";

/* ------------------------------------------------------------------ data */

type Item = {
	amount: string;
	unit: string;
	img: string;
	price: string;
	total: number;
	badge?: string;
	note?: string;
	perks?: string;
	showCart?: boolean;
};

type Section = { id: string; title: string; items: Item[] };

const SECTIONS: Section[] = [
	{
		id: "offers",
		title: "SPECIAL OFFERS",
		items: [
			{
				amount: "45,000,000",
				unit: "COINS + 3 BOOSTS",
				img: PURSE,
				price: "$ 4.99",
				total: 45000000,
				badge: "BEST\nVALUE",
			},
			{
				amount: "360,000,000",
				unit: "COINS + VAULT KEY",
				img: PURSE,
				price: "$ 19.99",
				total: 360000000,
				badge: "+20%\nBONUS",
			},
			{
				amount: "1,200,000,000",
				unit: "COINS + 10 BOOSTS",
				img: DUFFEL,
				price: "$ 44.99",
				total: 1200000000,
				badge: "+25%\nBONUS",
			},
		],
	},
	{
		id: "coins",
		title: "COIN PACKS",
		items: [
			{ amount: "15,000,000", unit: "COINS", img: TRIO, price: "$ 1.99", total: 15000000 },
			{
				amount: "45,000,000",
				unit: "COINS",
				img: STACK,
				price: "$ 4.99",
				total: 45000000,
				badge: "+10%\nBONUS",
			},
			{
				amount: "135,000,000",
				unit: "COINS",
				img: STACK,
				price: "$ 9.99",
				total: 135000000,
				badge: "+10%\nBONUS",
			},
			{
				amount: "495,000,000",
				unit: "COINS",
				img: PURSE,
				price: "$ 24.99",
				total: 495000000,
				badge: "MOST\nPOPULAR",
			},
			{
				amount: "1,450,000,000",
				unit: "COINS",
				img: SACK,
				price: "$ 49.99",
				total: 1450000000,
				badge: "+15%\nBONUS",
			},
			{
				amount: "4,050,000,000",
				unit: "COINS",
				img: DUFFEL,
				price: "$ 99.99",
				total: 4050000000,
				badge: "BEST\nVALUE",
			},
		],
	},
	{
		id: "club",
		title: "CLUB PASS",
		items: [
			{
				amount: "GOLD PASS",
				unit: "30 DAYS",
				img: SACK,
				price: "$ 9.99",
				total: 180000000,
				perks: "6M coin drop every day · Daily free spin refill · Gold nickname frame",
			},
			{
				amount: "PLATINUM PASS",
				unit: "30 DAYS",
				img: LOCK,
				price: "$ 29.99",
				total: 630000000,
				badge: "+15%\nBONUS",
				perks:
					"All Gold Pass rewards · 21M coin drop every day · Extra vault slot · Skip 20 club tiers instantly",
			},
		],
	},
	{
		id: "free",
		title: "FREE GIFT",
		items: [
			{
				amount: "250,000",
				unit: "BONUS COINS",
				img: TRIO,
				price: "Claim",
				total: 250000,
				showCart: false,
				note: "Availability daily: 1/1",
			},
			{
				amount: "1 VAULT KEY",
				unit: "WEEKLY GIFT",
				img: LOCK,
				price: "Claim",
				total: 0,
				showCart: false,
				note: "Availability weekly: 1/1",
			},
		],
	},
];

const FAQ: Array<[string, string]> = [
	[
		"How do I find my Player ID?",
		"Open Settings in the game — your Player ID sits next to your player name. Enter it at checkout so coins land on the right account.",
	],
	[
		"Why is the web shop cheaper than in-game?",
		"Buying here skips app-store fees, so the same price carries a larger coin total and bonus multipliers.",
	],
	[
		"My purchase was cancelled — what now?",
		"Cancelled payments are never charged. Retry with another method at checkout, or contact support with your order reference.",
	],
	[
		"I bought a pack but my balance has not updated.",
		"Coins are usually credited in seconds. If the balance still looks stale after a minute, return to the lobby or reload the game client.",
	],
	[
		"What is Xsolla?",
		"Xsolla is our authorised merchant of record. They process the payment and issue the receipt; card data never reaches the game client.",
	],
	[
		"What about security?",
		"All transactions run over encrypted connections and are monitored for fraud. We never store full card numbers.",
	],
];

/* ----------------------------------------------------------------- utils */

const fmt = (n: number) => n.toLocaleString("en-US");
const short = (n: number) =>
	n >= 1e9
		? Math.round(n / 1e8) / 10 + "B"
		: n >= 1e6
			? Math.round(n / 1e6) + "M"
			: n >= 1e3
				? Math.round(n / 1e3) + "K"
				: String(n);
const pad = (n: number) => String(n).padStart(2, "0");

/* --------------------------------------------------- injected global CSS */

const FONTS_HREF =
	"https://fonts.googleapis.com/css2?family=Archivo+Black&family=Barlow:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap";

/* Layered page backdrop: a deep navy base, three coloured glows that drift down the
   page, a fine casino pinstripe and a vignette. Sections sit on top of it transparently
   so the whole page reads as one lit room rather than a stack of flat bands. */
const BACKDROP =
	"radial-gradient(900px 540px at 10% -4%,rgba(108,43,217,.42),transparent 60%)," +
	"radial-gradient(820px 520px at 90% 6%,rgba(42,85,196,.46),transparent 62%)," +
	"radial-gradient(1100px 760px at 50% 44%,rgba(27,73,168,.30),transparent 66%)," +
	"radial-gradient(760px 520px at 82% 88%,rgba(255,215,106,.10),transparent 62%)," +
	"linear-gradient(180deg,#070c20 0%,#0c1a42 34%,#0a1533 68%,#060a1c 100%)";

const CSS = `
html,body{margin:0;padding:0;background:#070c20}
.qhs{color:#fff;font-family:Barlow,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.qhs *{box-sizing:border-box}
.qhs a{color:#7FD4FF;text-decoration:none}
.qhs a:hover{color:#C7ECFF;text-decoration:underline}
.qhs button{font-family:inherit}
.qhs :focus-visible{outline:3px solid #7FD4FF;outline-offset:3px}
@keyframes qhs-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes qhs-rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@keyframes qhs-drift{0%,100%{transform:translate3d(-5%,-3%,0) scale(1)}50%{transform:translate3d(5%,4%,0) scale(1.12)}}
@media (prefers-reduced-motion:reduce){.qhs *{animation:none!important}}
.qhs-btn:hover{filter:brightness(1.12)}
.qhs-btn:active{transform:translateY(2px);box-shadow:0 2px 0 ${CTA_SHADOW}}
.qhs-flat:hover{filter:brightness(1.12)}
.qhs-btn3:hover{filter:brightness(1.12)}
.qhs-btn3:active{transform:translateY(3px);box-shadow:0 2px 0 ${CTA_SHADOW}}
.qhs-card:hover{border-color:#FFD76A}
.qhs-nav:hover{color:#C7ECFF;text-decoration:underline}
.qhs-tab:hover{color:#FFD76A;text-decoration:none}
.qhs-faq:hover{color:#FFD76A}
.qhs-store-cta:hover{border-color:#FFD76A;text-decoration:none}
.qhs-social:hover{color:#FFD76A;text-decoration:none}
.qhs-close:hover{filter:brightness(1.1)}
.qhs-cancel:hover{border-color:#7FD4FF}
`;

function useGlobalStyles() {
	useEffect(() => {
		const head = document.head;
		const nodes: Node[] = [];

		if (!head.querySelector('link[data-qhs-fonts="1"]')) {
			const pre = document.createElement("link");
			pre.rel = "preconnect";
			pre.href = "https://fonts.gstatic.com";
			pre.crossOrigin = "";
			head.appendChild(pre);
			nodes.push(pre);

			const link = document.createElement("link");
			link.rel = "stylesheet";
			link.href = FONTS_HREF;
			link.setAttribute("data-qhs-fonts", "1");
			head.appendChild(link);
			nodes.push(link);
		}

		if (!head.querySelector('style[data-qhs-css="1"]')) {
			const style = document.createElement("style");
			style.setAttribute("data-qhs-css", "1");
			style.textContent = CSS;
			head.appendChild(style);
			nodes.push(style);
		}

		return () => {
			nodes.forEach((n) => {
				if (n.parentNode) n.parentNode.removeChild(n);
			});
		};
	}, []);
}

/* ------------------------------------------------------- Xsolla Login */

// The landing is already bound to this Login project (landing doc: auth.loginId,
// auth.type === "login"), so the widget below signs players in against the same
// project Site Builder's own auth would use.
const LOGIN_PROJECT_ID = "YOUR_LOGIN_PROJECT_ID";
const LOGIN_SDK_SRC = "https://login-sdk.xsolla.com/latest/";
const LOGIN_API = "https://login.xsolla.com/api";
const TOKEN_KEY = "qhs.xsolla.token";

// The Login SDK attaches itself to window; this block renders client-side only
// (the block is stored with skipSsr), but guard anyway so import never throws.
const WIN: any = typeof window !== "undefined" ? window : {};

type Player = { id: string; name: string };

const readToken = (): string => {
	try {
		return window.localStorage.getItem(TOKEN_KEY) || "";
	} catch (e) {
		return "";
	}
};

const writeToken = (t: string) => {
	try {
		if (t) window.localStorage.setItem(TOKEN_KEY, t);
		else window.localStorage.removeItem(TOKEN_KEY);
	} catch (e) {
		// Private mode / blocked storage — the session just won't survive a reload.
	}
};

// A Login JWT is three base64url segments; the middle one carries `exp`.
const tokenIsLive = (t: string) => {
	try {
		const claims = JSON.parse(
			atob(t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
		);
		return !claims.exp || claims.exp * 1000 > Date.now();
	} catch (e) {
		return false;
	}
};

// The widget sends the player back to callbackUrl?token=<jwt>. Take the token, then
// scrub it from the address bar so a refresh or a copied link doesn't carry it around.
const harvestToken = (): string => {
	try {
		const url = new URL(window.location.href);
		const t = url.searchParams.get("token") || "";
		if (!t) return "";
		url.searchParams.delete("token");
		window.history.replaceState({}, document.title, url.toString());
		return t;
	} catch (e) {
		return "";
	}
};

function useXsollaAuth() {
	const [player, setPlayer] = useState<Player | null>(null);
	const [busy, setBusy] = useState(false);
	const widget: any = useRef(null);

	useEffect(() => {
		const fresh = harvestToken();
		if (fresh) writeToken(fresh);
		const token = fresh || readToken();
		if (!token) return;
		if (!tokenIsLive(token)) {
			writeToken("");
			return;
		}
		let cancelled = false;
		fetch(LOGIN_API + "/users/me", { headers: { Authorization: "Bearer " + token } })
			.then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
			.then((u) => {
				if (cancelled) return;
				setPlayer({ id: u.id || "", name: u.nickname || u.username || u.email || "Player" });
			})
			.catch(() => {
				if (cancelled) return;
				writeToken("");
				setPlayer(null);
			});
		return () => {
			cancelled = true;
		};
	}, []);

	const signIn = () => {
		setBusy(true);
		const start = () => {
			const XL = WIN.XsollaLogin;
			if (!XL) {
				setBusy(false);
				return;
			}
			if (!widget.current) {
				widget.current = new XL.Widget({
					projectId: LOGIN_PROJECT_ID,
					preferredLocale: "en_US",
					callbackUrl: window.location.origin + window.location.pathname,
					popupBackgroundColor: "rgba(4,7,22,.82)",
				});
			}
			widget.current.open();
			setBusy(false);
		};

		if (WIN.XsollaLogin) {
			start();
			return;
		}
		const existing = document.querySelector('script[data-qhs-login="1"]');
		if (existing) {
			existing.addEventListener("load", start);
			return;
		}
		const s = document.createElement("script");
		s.src = LOGIN_SDK_SRC;
		s.async = true;
		s.setAttribute("data-qhs-login", "1");
		s.onload = start;
		s.onerror = () => setBusy(false);
		document.head.appendChild(s);
	};

	const signOut = () => {
		writeToken("");
		setPlayer(null);
	};

	return { player, busy, signIn, signOut };
}

/* ------------------------------------------------------------ components */

const AB = "'Archivo Black',sans-serif";
const MONO = "'IBM Plex Mono',monospace";

function Badge({ text }: { text: string }) {
	return (
		<div
			style={{
				position: "absolute",
				top: 8,
				right: 8,
				width: 58,
				height: 58,
				borderRadius: "50%",
				background: "radial-gradient(circle at 40% 35%,#FF6B6B,#C0201A)",
				border: "2px solid #FFD0CB",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				textAlign: "center",
				fontFamily: AB,
				fontSize: 10,
				lineHeight: 1.1,
				color: "#fff",
				whiteSpace: "pre-line",
				transform: "rotate(-12deg)",
				boxShadow: "0 6px 14px rgba(0,0,0,.4)",
			}}
		>
			{text}
		</div>
	);
}

function Card({ item, onBuy }: { item: Item; onBuy: () => void }) {
	const showCart = item.showCart !== false;
	return (
		<div
			className="qhs-card"
			style={{
				position: "relative",
				width: 236,
				display: "flex",
				flexDirection: "column",
				borderRadius: 12,
				overflow: "hidden",
				background: "#0b1a3d",
				border: "1px solid rgba(255,255,255,.14)",
				boxShadow: "0 10px 26px rgba(0,0,0,.35)",
			}}
		>
			<div
				style={{
					position: "relative",
					padding: "12px 12px 10px",
					textAlign: "center",
					background: "linear-gradient(180deg,#1b3e8f,#122c6b)",
				}}
			>
				<div
					style={{
						fontFamily: AB,
						fontSize: 19,
						lineHeight: 1.1,
						color: "#fff",
						textShadow: "0 2px 0 rgba(0,0,0,.4)",
					}}
				>
					{item.amount}
				</div>
				<div
					style={{
						fontFamily: MONO,
						fontSize: 10.5,
						letterSpacing: ".12em",
						color: "#BFD4FF",
						marginTop: 2,
					}}
				>
					{item.unit}
				</div>
			</div>

			<div
				style={{
					position: "relative",
					height: 128,
					background: "radial-gradient(240px 140px at 50% 25%,#2a55c4,#0e1f4f)",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
				}}
			>
				<img
					src={item.img}
					alt=""
					style={{
						maxWidth: "82%",
						maxHeight: 106,
						objectFit: "contain",
						filter: "drop-shadow(0 10px 14px rgba(0,0,0,.45))",
					}}
				/>
				{item.badge ? <Badge text={item.badge} /> : null}
			</div>

			{item.perks ? (
				<div
					style={{
						padding: "12px 14px",
						fontSize: 12.5,
						lineHeight: 1.6,
						color: "#C6D6FF",
						background: "#0b1a3d",
					}}
				>
					{item.perks}
				</div>
			) : null}

			<div
				style={{
					marginTop: "auto",
					display: "flex",
					gap: 6,
					padding: "10px 10px 12px",
					background: "#0b1a3d",
				}}
			>
				<button
					type="button"
					className="qhs-btn"
					onClick={onBuy}
					style={{
						flex: 1,
						height: 44,
						borderRadius: 9,
						border: "none",
						background: CTA,
						color: "#fff",
						fontFamily: AB,
						fontSize: 15,
						cursor: "pointer",
						boxShadow: "0 4px 0 " + CTA_SHADOW,
					}}
				>
					{item.price}
				</button>
				{showCart ? (
					<button
						type="button"
						className="qhs-flat"
						onClick={onBuy}
						aria-label="Add to cart"
						style={{
							width: 44,
							height: 44,
							borderRadius: 9,
							border: "none",
							background: CTA,
							color: "#fff",
							fontSize: 15,
							cursor: "pointer",
							boxShadow: "0 4px 0 " + CTA_SHADOW,
						}}
					>
						🛒
					</button>
				) : null}
			</div>

			{item.note ? (
				<div
					style={{
						padding: "0 12px 12px",
						textAlign: "center",
						fontFamily: MONO,
						fontSize: 10,
						color: "#8FA2D4",
						background: "#0b1a3d",
					}}
				>
					{item.note}
				</div>
			) : null}
		</div>
	);
}

/* ----------------------------------------------------------------- shell */

export default function QuickHitSlotsShop() {
	useGlobalStyles();

	const { player, busy, signIn, signOut } = useXsollaAuth();
	const [modal, setModal] = useState<Item | null>(null);
	const [phase, setPhase] = useState<"idle" | "processing">("idle");
	const [toast, setToast] = useState("");
	const [open, setOpen] = useState(0);
	const [left, setLeft] = useState(9 * 3600 + 42 * 60 + 18);

	const t2 = useRef<ReturnType<typeof setTimeout> | null>(null);
	const t3 = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(() => {
		const timer = setInterval(() => setLeft((s) => (s > 0 ? s - 1 : 0)), 1000);
		return () => {
			clearInterval(timer);
			if (t2.current) clearTimeout(t2.current);
			if (t3.current) clearTimeout(t3.current);
		};
	}, []);

	const sections = SECTIONS.filter((s) => SHOW_FREE_GIFT || s.id !== "free");
	const tabs = sections.map((s) => ({ label: s.title, href: "#" + s.id }));

	const openModal = (item: Item) => {
		setModal(item);
		setPhase("idle");
	};
	const closeModal = () => {
		setModal(null);
		setPhase("idle");
	};
	const confirm = () => {
		if (!modal || phase === "processing") return;
		const p = modal;
		setPhase("processing");
		t2.current = setTimeout(() => {
			setModal(null);
			setPhase("idle");
			setToast(fmt(p.total) + " coins credited");
			t3.current = setTimeout(() => setToast(""), 3400);
		}, 1300);
	};

	const h = Math.floor(left / 3600);
	const m = Math.floor((left % 3600) / 60);
	const sec = left % 60;
	const countdown = pad(h) + ":" + pad(m) + ":" + pad(sec);

	const welcome = SECTIONS[0].items[0];

	return (
		<div className="qhs" style={{ position: "relative", minHeight: "100vh", background: BACKDROP }}>
			{/* ------------------------------------------------------- backdrop */}
			<div
				aria-hidden="true"
				style={{
					position: "fixed",
					inset: "-15%",
					zIndex: 0,
					pointerEvents: "none",
					background:
						"radial-gradient(closest-side,rgba(108,43,217,.30),transparent 70%)," +
						"radial-gradient(closest-side,rgba(255,215,106,.10),transparent 70%)",
					backgroundSize: "70% 70%, 55% 55%",
					backgroundPosition: "8% 12%, 88% 78%",
					backgroundRepeat: "no-repeat",
					filter: "blur(40px)",
					animation: "qhs-drift 26s ease-in-out infinite",
				}}
			/>
			<div
				aria-hidden="true"
				style={{
					position: "fixed",
					inset: 0,
					zIndex: 0,
					pointerEvents: "none",
					background:
						"repeating-linear-gradient(115deg,rgba(255,255,255,.035) 0 2px,transparent 2px 46px)",
				}}
			/>
			<div
				aria-hidden="true"
				style={{
					position: "fixed",
					inset: 0,
					zIndex: 0,
					pointerEvents: "none",
					background: "radial-gradient(125% 85% at 50% 45%,transparent 42%,rgba(2,5,16,.62) 100%)",
				}}
			/>

			<div style={{ position: "relative", zIndex: 1 }}>
			{/* ---------------------------------------------------------- header */}
			<header
				style={{
					position: "sticky",
					top: 0,
					zIndex: 40,
					background: "rgba(8,14,38,.78)",
					backdropFilter: "blur(16px)",
					WebkitBackdropFilter: "blur(16px)",
					borderBottom: "1px solid rgba(255,214,106,.18)",
					boxShadow: "0 10px 30px rgba(2,5,16,.45)",
				}}
			>
				<div
					style={{
						maxWidth: 1180,
						margin: "0 auto",
						padding: "10px 20px",
						display: "flex",
						alignItems: "center",
						gap: 18,
					}}
				>
					<nav
						aria-label="Primary"
						style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}
					>
						<a className="qhs-nav" href="#top" style={{ fontSize: 14, fontWeight: 600, color: "#DCE7FF" }}>
							Home
						</a>
						<a className="qhs-nav" href="#coins" style={{ fontSize: 14, fontWeight: 600, color: "#FFD76A" }}>
							Coin packs
						</a>
						<a className="qhs-nav" href="#club" style={{ fontSize: 14, fontWeight: 600, color: "#DCE7FF" }}>
							Club pass
						</a>
						<a className="qhs-nav" href="#free" style={{ fontSize: 14, fontWeight: 600, color: "#DCE7FF" }}>
							Free gift
						</a>
					</nav>
					<div style={{ flex: 1 }} />
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 10,
							position: "absolute",
							left: "50%",
							transform: "translateX(-50%)",
						}}
					>
						<img
							src={KEYART}
							alt=""
							style={{
								width: 34,
								height: 34,
								borderRadius: 9,
								objectFit: "cover",
								border: "1px solid rgba(255,214,106,.6)",
							}}
						/>
						<div
							style={{
								fontFamily: AB,
								fontSize: 14,
								letterSpacing: ".04em",
								lineHeight: 1.05,
								color: "#FFD76A",
							}}
						>
							QUICK HIT
							<br />
							<span style={{ color: "#fff", fontSize: 11, letterSpacing: ".18em" }}>SLOTS</span>
						</div>
					</div>
					<div style={{ display: "flex", alignItems: "center", gap: 10 }}>
						<button
							type="button"
							className="qhs-flat"
							style={{
								height: 40,
								padding: "0 16px",
								borderRadius: 10,
								border: "none",
								background: CTA,
								color: "#fff",
								fontWeight: 700,
								fontSize: 13,
								cursor: "pointer",
							}}
						>
							🛒 Cart
						</button>
						{player ? (
							<>
								<div
									title={player.name}
									style={{
										display: "flex",
										alignItems: "center",
										gap: 8,
										maxWidth: 190,
										height: 40,
										padding: "0 14px",
										borderRadius: 10,
										background: "rgba(18,34,79,.9)",
										border: "1px solid rgba(255,214,106,.4)",
									}}
								>
									<div
										style={{
											width: 20,
											height: 20,
											flex: "none",
											borderRadius: "50%",
											background:
												"radial-gradient(circle at 35% 30%,#FFE9A3,#E0A62C 60%,#9A6A12)",
											color: "#1B2A6B",
											fontFamily: AB,
											fontSize: 10,
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
										}}
									>
										{player.name.slice(0, 1).toUpperCase()}
									</div>
									<span
										style={{
											fontWeight: 700,
											fontSize: 13,
											color: "#FFD76A",
											overflow: "hidden",
											textOverflow: "ellipsis",
											whiteSpace: "nowrap",
										}}
									>
										{player.name}
									</span>
								</div>
								<button
									type="button"
									className="qhs-flat"
									onClick={signOut}
									style={{
										height: 40,
										padding: "0 14px",
										borderRadius: 10,
										border: "2px solid rgba(159,180,232,.4)",
										background: "transparent",
										color: "#DCE7FF",
										fontWeight: 700,
										fontSize: 13,
										cursor: "pointer",
									}}
								>
									Log out
								</button>
							</>
						) : (
							<button
								type="button"
								className="qhs-flat"
								onClick={signIn}
								disabled={busy}
								style={{
									height: 40,
									padding: "0 18px",
									borderRadius: 10,
									border: "none",
									background: CTA,
									color: "#fff",
									fontWeight: 700,
									fontSize: 13,
									cursor: busy ? "progress" : "pointer",
									opacity: busy ? 0.75 : 1,
								}}
							>
								{busy ? "Opening…" : "Login"}
							</button>
						)}
					</div>
				</div>
			</header>

			{/* ------------------------------------------------------------ hero */}
			<section
				id="top"
				style={{
					position: "relative",
					padding: "30px 20px 34px",
					background:
						"radial-gradient(900px 420px at 50% 40%,rgba(31,72,166,.55),transparent 70%)",
					overflow: "hidden",
				}}
			>
				<div
					style={{
						position: "relative",
						maxWidth: 1080,
						margin: "0 auto",
						borderRadius: 16,
						overflow: "hidden",
						border: "2px solid rgba(255,214,106,.55)",
						background:
							"radial-gradient(760px 340px at 25% 0%,#2a55c4 0%,#16307c 45%,#0d1a48 100%)",
						boxShadow: "0 22px 50px rgba(0,0,0,.45)",
					}}
				>
					<div
						style={{
							display: "flex",
							gap: 24,
							alignItems: "center",
							padding: "22px 26px",
							flexWrap: "wrap",
						}}
					>
						<div style={{ flex: 1, minWidth: 280 }}>
							<div
								style={{
									display: "inline-block",
									padding: "5px 12px",
									borderRadius: 6,
									background: "rgba(255,255,255,.92)",
									color: "#1B2A6B",
									fontFamily: AB,
									fontSize: 11,
									letterSpacing: ".08em",
								}}
							>
								SPECIAL OFFER
							</div>
							<h1
								style={{
									margin: "12px 0 10px",
									fontFamily: AB,
									fontSize: 34,
									lineHeight: 1.04,
									textShadow: "0 3px 0 rgba(0,0,0,.35)",
								}}
							>
								WELCOME OFFER
							</h1>
							<div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
								{[
									["45M", "COINS"],
									["3", "BOOSTS"],
									["1", "VAULT KEY"],
								].map(([v, l]) => (
									<div
										key={l}
										style={{
											minWidth: 74,
											padding: "8px 10px",
											borderRadius: 10,
											background: "rgba(6,12,36,.55)",
											border: "1px solid rgba(255,214,106,.35)",
											textAlign: "center",
										}}
									>
										<div style={{ fontFamily: AB, fontSize: 15, color: "#FFD76A" }}>{v}</div>
										<div style={{ fontFamily: MONO, fontSize: 10, color: "#9FB4E8" }}>{l}</div>
									</div>
								))}
							</div>
							<div style={{ display: "flex", alignItems: "center", gap: 8, maxWidth: 420 }}>
								<button
									type="button"
									className="qhs-btn"
									onClick={() => openModal(welcome)}
									style={{
										flex: 1,
										height: 44,
										borderRadius: 10,
										border: "none",
										background: CTA,
										color: "#fff",
										fontFamily: AB,
										fontSize: 16,
										cursor: "pointer",
										boxShadow: "0 4px 0 " + CTA_SHADOW,
									}}
								>
									$ 4.99
								</button>
								<button
									type="button"
									className="qhs-flat"
									onClick={() => openModal(welcome)}
									aria-label="Add welcome offer to cart"
									style={{
										width: 46,
										height: 44,
										borderRadius: 10,
										border: "none",
										background: CTA,
										color: "#fff",
										fontSize: 16,
										cursor: "pointer",
										boxShadow: "0 4px 0 " + CTA_SHADOW,
									}}
								>
									🛒
								</button>
							</div>
							<div style={{ marginTop: 8, fontFamily: MONO, fontSize: 11, color: "#9FB4E8" }}>
								AVAILABLE 1/1 · ENDS IN {countdown}
							</div>
						</div>
						<div
							style={{
								position: "relative",
								width: 260,
								height: 170,
								flex: "none",
								animation: "qhs-bob 5.5s ease-in-out infinite",
							}}
						>
							<img
								src={DUFFEL}
								alt="Welcome offer coin bundle"
								style={{
									position: "absolute",
									inset: 0,
									width: "100%",
									height: "100%",
									objectFit: "contain",
									filter: "drop-shadow(0 14px 22px rgba(0,0,0,.5))",
								}}
							/>
							<div
								style={{
									position: "absolute",
									top: -14,
									right: -10,
									width: 62,
									height: 62,
									borderRadius: "50%",
									background: "radial-gradient(circle at 35% 30%,#FFF0BE,#E8B334 58%,#8C5F0E)",
									border: "3px solid #FFF3CC",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									fontFamily: AB,
									fontSize: 19,
									color: "#1B2A6B",
								}}
							>
								3X
							</div>
						</div>
					</div>
				</div>
			</section>

			{/* ----------------------------------------------------------- store */}
			<h2
				style={{
					margin: 0,
					padding: "26px 20px 18px",
					textAlign: "center",
					fontFamily: AB,
					fontSize: 26,
					letterSpacing: ".06em",
					background: "transparent",
					textShadow: "0 0 34px rgba(255,215,106,.35)",
				}}
			>
				STORE
			</h2>

			<nav
				aria-label="Store sections"
				style={{
					position: "sticky",
					top: 60,
					zIndex: 30,
					background: "linear-gradient(180deg,rgba(28,72,164,.92),rgba(14,36,92,.92))",
					backdropFilter: "blur(12px)",
					WebkitBackdropFilter: "blur(12px)",
					borderTop: "1px solid rgba(255,255,255,.14)",
					borderBottom: "1px solid rgba(255,214,106,.35)",
					boxShadow: "0 12px 28px rgba(2,5,16,.4)",
				}}
			>
				<div
					style={{
						maxWidth: 1080,
						margin: "0 auto",
						padding: "0 20px",
						display: "flex",
						gap: 10,
						justifyContent: "center",
						flexWrap: "wrap",
					}}
				>
					{tabs.map((tab) => (
						<a
							key={tab.href}
							className="qhs-tab"
							href={tab.href}
							style={{
								minHeight: 44,
								display: "flex",
								alignItems: "center",
								padding: "0 18px",
								fontFamily: AB,
								fontSize: 12.5,
								letterSpacing: ".07em",
								color: "#DCE7FF",
								textDecoration: "none",
							}}
						>
							{tab.label}
						</a>
					))}
				</div>
			</nav>

			<div style={{ background: "transparent", padding: "8px 20px 46px" }}>
				<div style={{ maxWidth: 1080, margin: "0 auto" }}>
					{sections.map((sec) => (
						<section key={sec.id} id={sec.id} style={{ padding: "28px 0 6px", scrollMarginTop: 118 }}>
							<h3
								style={{
									margin: "0 0 18px",
									textAlign: "center",
									fontFamily: AB,
									fontSize: 14,
									letterSpacing: ".14em",
									color: "#fff",
								}}
							>
								{sec.title}
							</h3>
							<div
								style={{
									display: "flex",
									flexWrap: "wrap",
									gap: 16,
									justifyContent: "center",
								}}
							>
								{sec.items.map((item, i) => (
									<Card key={sec.id + i} item={item} onBuy={() => openModal(item)} />
								))}
							</div>
						</section>
					))}
				</div>
			</div>

			{/* ------------------------------------------------------------- faq */}
			<section style={{ background: "transparent", padding: "44px 20px 50px" }}>
				<h3
					style={{
						margin: "0 0 22px",
						textAlign: "center",
						fontFamily: AB,
						fontSize: 20,
						letterSpacing: ".1em",
					}}
				>
					FAQ
				</h3>
				<div style={{ maxWidth: 880, margin: "0 auto", display: "grid", gap: 8 }}>
					{FAQ.map((f, i) => (
						<div
							key={f[0]}
							style={{
								borderRadius: 8,
								background: "rgba(18,28,64,.72)",
								backdropFilter: "blur(8px)",
								WebkitBackdropFilter: "blur(8px)",
								border: "1px solid rgba(255,255,255,.10)",
								overflow: "hidden",
							}}
						>
							<button
								type="button"
								className="qhs-faq"
								onClick={() => setOpen(open === i ? -1 : i)}
								style={{
									width: "100%",
									minHeight: 48,
									display: "flex",
									alignItems: "center",
									gap: 12,
									padding: "12px 16px",
									background: "transparent",
									border: "none",
									color: "#fff",
									fontSize: 14,
									fontWeight: 600,
									textAlign: "left",
									cursor: "pointer",
								}}
							>
								<span style={{ color: "#7FD4FF", fontSize: 12 }}>{open === i ? "▲" : "▼"}</span>
								{f[0]}
							</button>
							{open === i ? (
								<div
									style={{
										padding: "0 16px 16px 44px",
										fontSize: 13.5,
										lineHeight: 1.6,
										color: "#B9C8EE",
									}}
								>
									{f[1]}
								</div>
							) : null}
						</div>
					))}
				</div>
			</section>

			{/* ------------------------------------------------------------- cta */}
			<section
				style={{
					background: "radial-gradient(760px 380px at 50% 30%,rgba(35,86,198,.55),transparent 72%)",
					padding: "50px 20px 44px",
					textAlign: "center",
				}}
			>
				<img
					src={KEYART}
					alt="Quick Hit Slots key art"
					style={{
						width: "min(300px,80%)",
						borderRadius: 16,
						margin: "0 auto 22px",
						display: "block",
						boxShadow: "0 18px 44px rgba(0,0,0,.5)",
					}}
				/>
				<div
					style={{
						display: "flex",
						gap: 12,
						justifyContent: "center",
						flexWrap: "wrap",
						marginBottom: 22,
					}}
				>
					{[
						["App Store", "#ios"],
						["Google Play", "#android"],
					].map(([label, href]) => (
						<a
							key={href}
							className="qhs-store-cta"
							href={href}
							style={{
								minHeight: 48,
								display: "flex",
								alignItems: "center",
								padding: "0 22px",
								borderRadius: 10,
								background: "#0b1430",
								border: "1px solid rgba(255,255,255,.25)",
								color: "#fff",
								fontWeight: 700,
								fontSize: 14,
								textDecoration: "none",
							}}
						>
							{label}
						</a>
					))}
				</div>
				<h3 style={{ margin: 0, fontFamily: AB, fontSize: 24, lineHeight: 1.2, letterSpacing: ".01em" }}>
					SPIN THE REELS — YOUR COINS ARE
					<br />
					WAITING BACK IN THE GAME
				</h3>
			</section>

			{/* ---------------------------------------------------------- footer */}
			<footer
				style={{
					background: "linear-gradient(180deg,rgba(6,10,28,.50),rgba(3,6,18,.94))",
					borderTop: "1px solid rgba(255,255,255,.07)",
					padding: "28px 20px 34px",
				}}
			>
				<div
					style={{
						maxWidth: 1080,
						margin: "0 auto",
						display: "flex",
						gap: 22,
						alignItems: "center",
						flexWrap: "wrap",
					}}
				>
					<img
						src={KEYART}
						alt=""
						style={{ width: 70, height: 70, objectFit: "cover", borderRadius: 12 }}
					/>
					<div style={{ display: "flex", gap: 10 }}>
						{[
							["Facebook", "#facebook", "f"],
							["Instagram", "#instagram", "◎"],
						].map(([label, href, glyph]) => (
							<a
								key={href}
								className="qhs-social"
								href={href}
								aria-label={label}
								style={{
									width: 36,
									height: 36,
									borderRadius: 8,
									background: "#141f45",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									color: "#DCE7FF",
									textDecoration: "none",
								}}
							>
								{glyph}
							</a>
						))}
					</div>
					<div
						style={{
							flex: 1,
							minWidth: 240,
							fontFamily: MONO,
							fontSize: 11,
							lineHeight: 1.9,
							color: "#7789B8",
						}}
					>
						© 2026 QUICK HIT SLOTS · VIRTUAL COINS HAVE NO CASH VALUE · 21+
						<br />
						<a href="#support">Support</a> · Powered by Xsolla Web Shop ·{" "}
						<a href="#affiliate">Affiliate program</a> · <a href="#privacy">Privacy settings</a>
					</div>
				</div>
			</footer>

			{/* ----------------------------------------------------------- modal */}
			{modal ? (
				<div
					role="dialog"
					aria-modal="true"
					aria-label="Confirm purchase"
					style={{
						position: "fixed",
						inset: 0,
						zIndex: 80,
						background: "rgba(4,7,22,.78)",
						backdropFilter: "blur(6px)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						padding: 22,
					}}
				>
					<div
						style={{
							position: "relative",
							width: "min(540px,100%)",
							borderRadius: 18,
							padding: 2,
							background: "linear-gradient(135deg,#FFE79A,#C7902A 45%,#6E4E11 72%,#FFE79A)",
							boxShadow: "0 30px 80px rgba(0,0,0,.6)",
							animation: "qhs-rise .18s ease-out",
						}}
					>
						<div
							style={{
								borderRadius: 16,
								background:
									"radial-gradient(600px 300px at 50% -10%,#22499f 0%,#132a6d 45%,#0a1436 100%)",
								padding: "28px 28px 24px",
							}}
						>
							<button
								type="button"
								className="qhs-close"
								onClick={closeModal}
								aria-label="Close"
								style={{
									position: "absolute",
									top: -14,
									right: -14,
									width: 46,
									height: 46,
									borderRadius: 12,
									border: "3px solid #FFE0A0",
									background: "linear-gradient(180deg,#E05B4A,#A3231A)",
									color: "#fff",
									fontSize: 18,
									fontWeight: 700,
									cursor: "pointer",
									boxShadow: "0 8px 20px rgba(0,0,0,.5)",
								}}
							>
								✕
							</button>
							<div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".14em", color: "#7FD4FF" }}>
								{phase === "processing" ? "CONTACTING XSOLLA…" : "CONFIRM PURCHASE"}
							</div>
							<h2 style={{ margin: "10px 0 18px", fontFamily: AB, fontSize: 26, lineHeight: 1.1 }}>
								{modal.amount + " · " + modal.price}
							</h2>
							<div
								style={{
									display: "grid",
									gap: 10,
									padding: 16,
									borderRadius: 12,
									background: "rgba(6,12,36,.55)",
									border: "1px solid rgba(159,180,232,.22)",
								}}
							>
								<div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
									<span style={{ color: "#9FB4E8", fontSize: 14 }}>Base coins</span>
									<span style={{ fontWeight: 700 }}>{short(Math.round(modal.total / 3)) + " coins"}</span>
								</div>
								<div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
									<span style={{ color: "#9FB4E8", fontSize: 14 }}>Welcome multiplier</span>
									<span style={{ fontWeight: 700, color: "#6FE87C" }}>3×</span>
								</div>
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										gap: 12,
										paddingTop: 10,
										borderTop: "1px solid rgba(159,180,232,.2)",
									}}
								>
									<span style={{ color: "#9FB4E8", fontSize: 14 }}>Total credited</span>
									<span style={{ fontFamily: AB, color: "#FFD76A", fontSize: 18 }}>{fmt(modal.total)}</span>
								</div>
								<div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
									<span style={{ color: "#9FB4E8", fontSize: 14 }}>Charged to</span>
									<span
										style={{
											fontFamily: MONO,
											fontSize: 13,
											color: player ? "#fff" : "#8FA2D4",
										}}
									>
										{player ? player.name : "Not signed in"}
									</span>
								</div>
							</div>
							<div
								style={{
									marginTop: 20,
									display: "flex",
									gap: 12,
									flexWrap: "wrap",
									alignItems: "center",
								}}
							>
								<button
									type="button"
									className="qhs-btn3"
									onClick={confirm}
									style={{
										flex: 1,
										minWidth: 200,
										minHeight: 52,
										borderRadius: 12,
										border: "none",
										cursor: "pointer",
										background: CTA,
										color: "#fff",
										fontFamily: AB,
										fontSize: 17,
										boxShadow: "0 5px 0 " + CTA_SHADOW,
									}}
								>
									{phase === "processing" ? "Processing…" : "Continue to checkout"}
								</button>
								<button
									type="button"
									className="qhs-cancel"
									onClick={closeModal}
									style={{
										minHeight: 52,
										padding: "0 22px",
										borderRadius: 12,
										border: "2px solid rgba(159,180,232,.4)",
										background: "transparent",
										color: "#DCE7FF",
										fontWeight: 700,
										fontSize: 15,
										cursor: "pointer",
									}}
								>
									Cancel
								</button>
							</div>
							<div style={{ marginTop: 14, fontSize: 12, color: "#8FA2D4", lineHeight: 1.5 }}>
								You will be redirected to the Xsolla secure payment page. Virtual coins have no cash
								value.
							</div>
						</div>
					</div>
				</div>
			) : null}

			{/* ----------------------------------------------------------- toast */}
			{toast ? (
				<div
					role="status"
					style={{
						position: "fixed",
						left: "50%",
						bottom: 28,
						transform: "translateX(-50%)",
						zIndex: 90,
						display: "flex",
						alignItems: "center",
						gap: 12,
						padding: "14px 22px",
						borderRadius: 12,
						background: "linear-gradient(180deg,#153a1e,#0b2412)",
						border: "2px solid #4FBE5C",
						boxShadow: "0 18px 40px rgba(0,0,0,.5)",
						animation: "qhs-rise .18s ease-out",
					}}
				>
					<div
						style={{
							width: 26,
							height: 26,
							borderRadius: "50%",
							background: "#4FBE5C",
							color: "#062C0D",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							fontWeight: 800,
						}}
					>
						✓
					</div>
					<div style={{ fontWeight: 700, fontSize: 15, color: "#DFFFE5" }}>{toast}</div>
				</div>
			) : null}
			</div>
		</div>
	);
}
