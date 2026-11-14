from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.ticker import FuncFormatter

st.set_page_config(page_title="Olist E-Commerce Dashboard", page_icon="🛒", layout="wide")

HIGHLIGHT, GREY, ALERT = "#72BCD4", "#D3D3D3", "#E4572E"
rupiah_k = FuncFormatter(lambda x, _: f"R$ {x / 1e3:,.0f}K")


def clean_axes(ax):
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)


def show(fig):
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ---------- Data ----------
@st.cache_data
def load_data():
    return pd.read_csv(Path(__file__).parent / "main_data.csv", parse_dates=["order_date"])


def make_rfm(df):
    ref = df.order_date.max()
    rfm = df.groupby("customer_unique_id").agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("price", "sum"),
    ).reset_index()
    rfm["recency"] = (ref - rfm.last_order).dt.days
    rfm["r_score"] = pd.qcut(rfm.recency.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["m_score"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def segment(row):
        if row.frequency >= 2:
            return "Champions" if row.r_score >= 3 else "Repeat - Dormant"
        if row.r_score >= 4:
            return "New High Spender" if row.m_score >= 4 else "New Customer"
        if row.r_score <= 2 and row.m_score >= 4:
            return "At Risk (High Value)"
        return "Hibernating"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


df = load_data()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Filter")
    date_range = st.date_input(
        "Rentang tanggal order",
        value=(df.order_date.min().date(), df.order_date.max().date()),
        min_value=df.order_date.min().date(),
        max_value=df.order_date.max().date(),
    )
    all_states = sorted(df.customer_state.unique())
    chosen_states = st.multiselect("State pelanggan", all_states, default=all_states)
    st.caption("Filter berlaku untuk semua tab.")

if len(date_range) != 2:
    st.info("Pilih tanggal mulai dan tanggal akhir.")
    st.stop()

start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
fdf = df[(df.order_date >= start) & (df.order_date <= end) & (df.customer_state.isin(chosen_states))]
if fdf.empty:
    st.warning("Tidak ada data untuk filter ini.")
    st.stop()
odf = fdf.drop_duplicates("order_id")      # level order (satu baris per order)

# ---------- Header ----------
st.title("🛒 Olist E-Commerce Dashboard")
st.caption("Order berstatus delivered, Jan 2017 - Agu 2018. Revenue = harga barang tanpa ongkir.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Order", f"{odf.order_id.nunique():,}")
c2.metric("Total Revenue", f"R$ {fdf.price.sum():,.0f}")
c3.metric("Pelanggan Unik", f"{fdf.customer_unique_id.nunique():,}")
c4.metric("Rata-rata Review", f"{odf.review_score.mean():.2f} / 5")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Tren & Kategori", "Pengiriman & Review", "Pembayaran", "Segmentasi RFM", "Sebaran Geografis"]
)

# ---------- Tab 1: Pertanyaan 1 ----------
with tab1:
    st.subheader("Pertanyaan 1: Bagaimana tren order dan revenue bulanan, dan kategori apa yang teratas?")
    monthly = (fdf.groupby(fdf.order_date.dt.to_period("M"))
               .agg(revenue=("price", "sum"), order_count=("order_id", "nunique")))
    monthly.index = monthly.index.to_timestamp()
    monthly["revenue_mom_pct"] = monthly.revenue.pct_change() * 100

    metric = st.radio("Tampilkan tren", ["Revenue", "Jumlah order"], horizontal=True)
    col = "revenue" if metric == "Revenue" else "order_count"
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(monthly.index, monthly[col], marker="o", linewidth=2.5, color=HIGHLIGHT)
    pk = monthly[col].idxmax()
    ax.scatter(pk, monthly[col].max(), s=140, color=ALERT, zorder=5)
    near_end = (monthly.index.max() - pk).days < 90
    ax.annotate(f"Puncak {pk:%b %Y}", (pk, monthly[col].max()), xytext=(-8 if near_end else 0, 16),
                textcoords="offset points", ha="right" if near_end else "center", va="bottom",
                color=ALERT, fontsize=11, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))
    if col == "revenue":
        ax.yaxis.set_major_formatter(rupiah_k)
        ax.set_ylabel("Revenue per bulan (tanpa ongkir)")
    else:
        ax.set_ylabel("Jumlah order per bulan")
    ax.set_ylim(0, monthly[col].max() * 1.15)
    ax.set_title(f"{metric} per bulan", loc="left", fontsize=14, fontweight="bold")
    clean_axes(ax)
    show(fig)

    cat = (fdf.groupby("category").agg(revenue=("price", "sum"), orders=("order_id", "nunique"))
           .sort_values("revenue", ascending=False).reset_index())
    cat["share_pct"] = cat.revenue / cat.revenue.sum() * 100
    n = st.slider("Jumlah kategori teratas", 3, 15, 5)
    topn = cat.head(n).sort_values("revenue")
    fig, ax = plt.subplots(figsize=(11, 0.45 * n + 2))
    top_k = min(5, n)
    colors = [GREY] * (n - top_k) + [HIGHLIGHT] * top_k
    bars = ax.barh(topn.category, topn.revenue, color=colors)
    for b, s in zip(bars, topn.share_pct):
        ax.text(b.get_width() + topn.revenue.max() * 0.01, b.get_y() + b.get_height() / 2,
                f"{s:.1f}%", va="center", fontsize=10)
    ax.set_xlim(0, topn.revenue.max() * 1.12)
    ax.xaxis.set_major_formatter(rupiah_k)
    ax.set_xlabel("Total revenue")
    ax.set_title(f"{min(5, n)} kategori teratas menyumbang {cat.head(5).share_pct.sum():.0f}% revenue",
                 loc="left", fontsize=14, fontweight="bold")
    clean_axes(ax)
    show(fig)
    st.info(f"Revenue tertinggi pada **{pk:%b %Y}**. Kategori teratas: **{cat.iloc[0].category}** "
            f"({cat.iloc[0].share_pct:.1f}% revenue).")
    with st.expander("Tabel bulanan (termasuk MoM)"):
        st.dataframe(monthly.round(1))

# ---------- Tab 2: Pertanyaan 2 ----------
with tab2:
    st.subheader("Pertanyaan 2: State mana yang review-nya paling rendah dan pengirimannya paling lama?")
    only2018 = st.checkbox("Hanya Jan - Agu 2018 (sesuai notebook)", value=True)
    min_orders = st.slider("Minimal order per state", 10, 500, 100, step=10)
    base = odf[odf.order_date >= "2018-01-01"] if only2018 else odf

    nat = {"days": base.delivery_days.mean(), "review": base.review_score.mean(), "late": base.is_late.mean() * 100}
    st.caption(f"Rata-rata nasional: pengiriman {nat['days']:.1f} hari | review {nat['review']:.2f} | terlambat {nat['late']:.1f}%")

    sdf = (base.groupby("customer_state")
           .agg(order_count=("order_id", "nunique"), avg_review=("review_score", "mean"),
                avg_delivery_days=("delivery_days", "mean"), late_pct=("is_late", lambda s: s.mean() * 100))
           .reset_index())
    sdf = sdf[sdf.order_count >= min_orders].copy()

    if len(sdf) < 3:
        st.warning("Terlalu sedikit state yang memenuhi syarat. Turunkan batas minimal order atau perluas filter.")
    else:
        sdf["review_gap"] = sdf.avg_review - nat["review"]
        sdf["delivery_gap_days"] = sdf.avg_delivery_days - nat["days"]
        k = min(8, len(sdf))
        left, right = st.columns(2)
        with left:
            low = sdf.sort_values("avg_review").head(k).iloc[::-1]
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.barh(low.customer_state, low.review_gap, color=[GREY] * (k - 3) + [ALERT] * 3)
            ax.axvline(0, color="black", linewidth=1)
            for y, (gap, avg) in enumerate(zip(low.review_gap, low.avg_review)):
                ax.text(gap - 0.01, y, f"{avg:.2f}", va="center", ha="right", fontsize=10)
            ax.set_xlim(low.review_gap.min() * 1.4, 0.05)
            ax.set_xlabel("Selisih review vs rata-rata nasional (poin)")
            ax.set_title("State dengan review terendah", loc="left", fontsize=13, fontweight="bold")
            clean_axes(ax)
            show(fig)
        with right:
            slow = sdf.sort_values("avg_delivery_days", ascending=False).head(k).iloc[::-1]
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.barh(slow.customer_state, slow.avg_delivery_days, color=[GREY] * (k - 3) + [ALERT] * 3)
            ax.axvline(nat["days"], color="black", linestyle="--", linewidth=1)
            for y, v in enumerate(slow.avg_delivery_days):
                ax.text(v + 0.3, y, f"{v:.1f}", va="center", fontsize=10)
            ax.set_xlim(0, slow.avg_delivery_days.max() * 1.2)
            ax.set_xlabel("Rata-rata lama pengiriman (hari)  |  garis putus = nasional")
            ax.set_title("State dengan pengiriman terlama", loc="left", fontsize=13, fontweight="bold")
            clean_axes(ax)
            show(fig)

    late = (base.dropna(subset=["review_score"]).groupby("is_late")
            .agg(order_count=("order_id", "nunique"), avg_review=("review_score", "mean")).reset_index())
    if len(late) == 2:
        late["status"] = late.is_late.map({False: "Tepat waktu", True: "Terlambat"})
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(late.status, late.avg_review, color=[GREY, ALERT], width=0.55)
        for b, v, c in zip(bars, late.avg_review, late.order_count):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}\n({c:,} order)", ha="center", fontsize=10)
        ax.set_ylim(0, 5.3)
        ax.set_ylabel("Rata-rata review")
        gap = late.avg_review.iloc[0] - late.avg_review.iloc[1]
        ax.set_title(f"Order terlambat: review {gap:.1f} poin lebih rendah", loc="left", fontsize=13, fontweight="bold")
        clean_axes(ax)
        show(fig)
        corr = base[["delivery_days", "review_score"]].corr().iloc[0, 1]
        st.info(f"Korelasi lama pengiriman vs review = **{corr:.2f}**. Ini hubungan, belum tentu sebab-akibat.")
    with st.expander("Tabel per state"):
        st.dataframe(sdf.sort_values("avg_review").round(2))

# ---------- Tab 3: Pertanyaan 3 ----------
with tab3:
    st.subheader("Pertanyaan 3: Metode pembayaran dan cicilan apa yang dominan, dan kaitannya dengan nilai order?")
    pay = (odf.groupby("main_payment_type")
           .agg(order_count=("order_id", "nunique"), avg_value=("payment_total", "mean"))
           .sort_values("order_count").reset_index())
    pay["order_pct"] = pay.order_count / pay.order_count.sum() * 100
    colors = [HIGHLIGHT if t == pay.iloc[-1].main_payment_type else GREY for t in pay.main_payment_type]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), sharey=True)
    for ax, col, title, fmt in zip(axes, ["order_pct", "avg_value"],
                                   ["% dari jumlah order", "Rata-rata nilai order (R$, termasuk ongkir)"],
                                   ["{:.1f}%", "R$ {:.0f}"]):
        bars = ax.barh(pay.main_payment_type, pay[col], color=colors)
        for b, v in zip(bars, pay[col]):
            ax.text(v + pay[col].max() * 0.015, b.get_y() + b.get_height() / 2, fmt.format(v), va="center", fontsize=10)
        ax.set_xlim(0, pay[col].max() * 1.2)
        ax.set_title(title, loc="left", fontsize=12)
        clean_axes(ax)
    show(fig)

    cc = odf[odf.main_payment_type == "credit_card"].copy()
    if len(cc) > 0:
        cc["installment_group"] = pd.cut(cc.max_installments, bins=[0, 1, 3, 6, 10, 24],
                                         labels=["1x", "2-3x", "4-6x", "7-10x", ">10x"])
        inst = (cc.groupby("installment_group", observed=True)
                .agg(order_count=("order_id", "nunique"), avg_value=("payment_total", "mean")).reset_index())
        fig, ax = plt.subplots(figsize=(9, 4.5))
        bars = ax.bar(inst.installment_group.astype(str), inst.avg_value,
                      color=[ALERT if g == "7-10x" else GREY for g in inst.installment_group], width=0.6)
        for b, v, c in zip(bars, inst.avg_value, inst.order_count):
            ax.text(b.get_x() + b.get_width() / 2, v + inst.avg_value.max() * 0.02,
                    f"R$ {v:.0f}\n({c:,} order)", ha="center", fontsize=10)
        ax.set_ylim(0, inst.avg_value.max() * 1.25)
        ax.set_xlabel("Jumlah cicilan (hanya kartu kredit)")
        ax.set_ylabel("Rata-rata nilai order (R$)")
        ax.set_title("Semakin banyak cicilan, semakin besar nilai order", loc="left", fontsize=13, fontweight="bold")
        clean_axes(ax)
        show(fig)
    top = pay.iloc[-1]
    st.info(f"Metode terbanyak: **{top.main_payment_type}** ({top.order_pct:.1f}% order, "
            f"rata-rata R$ {top.avg_value:.0f}).")

# ---------- Tab 4: RFM ----------
with tab4:
    st.subheader("Analisis Lanjutan: Segmentasi Pelanggan (RFM)")
    st.caption("Recency = hari sejak belanja terakhir, Frequency = jumlah order, Monetary = total belanja. "
               "Skor R dan M memakai quintile; Frequency ditangani lewat aturan manual karena mayoritas pelanggan hanya belanja sekali.")
    if fdf.customer_unique_id.nunique() < 50:
        st.warning("Pelanggan terlalu sedikit untuk segmentasi. Perluas filter.")
    else:
        rfm = make_rfm(fdf)
        order_seg = ["Champions", "Repeat - Dormant", "New High Spender", "New Customer",
                     "At Risk (High Value)", "Hibernating"]
        seg = (rfm.groupby("segment")
               .agg(customers=("customer_unique_id", "nunique"), avg_recency=("recency", "mean"),
                    avg_monetary=("monetary", "mean"), total_revenue=("monetary", "sum"))
               .reindex(order_seg).dropna().reset_index())
        seg["customer_pct"] = seg.customers / seg.customers.sum() * 100
        seg["revenue_pct"] = seg.total_revenue / seg.total_revenue.sum() * 100
        cmap = {"At Risk (High Value)": ALERT, "Champions": HIGHLIGHT}
        cols = [cmap.get(s, GREY) for s in seg.segment]

        fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True)
        y = seg.segment[::-1]
        for ax, c, t in zip(axes, ["customer_pct", "revenue_pct"], ["% dari jumlah pelanggan", "% dari total revenue"]):
            vals = seg[c][::-1]
            bars = ax.barh(y, vals, color=cols[::-1])
            for b, v in zip(bars, vals):
                ax.text(v + 0.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=10)
            ax.set_xlim(0, max(seg.customer_pct.max(), seg.revenue_pct.max()) * 1.18)
            ax.set_title(t, loc="left", fontsize=12)
            clean_axes(ax)
        show(fig)
        st.info(f"Pelanggan yang hanya belanja sekali: **{(rfm.frequency == 1).mean() * 100:.1f}%**.")
        st.dataframe(seg.round(1))

# ---------- Tab 5: Geografis ----------
with tab5:
    st.subheader("Analisis Lanjutan: Sebaran Geografis Pelanggan")
    geo = (fdf.dropna(subset=["customer_lat", "customer_lng"]).drop_duplicates("customer_unique_id")
           .rename(columns={"customer_lat": "latitude", "customer_lng": "longitude"}))
    geo = geo[geo.latitude.between(-35, 6) & geo.longitude.between(-75, -33)]
    if len(geo) > 15000:
        geo = geo.sample(15000, random_state=42)
        st.caption("Peta menampilkan sampel acak 15.000 pelanggan agar tetap ringan.")
    st.map(geo[["latitude", "longitude"]], size=300)

    stt = (odf.groupby("customer_state").agg(orders=("order_id", "nunique")).reset_index()
           .sort_values("orders", ascending=False))
    stt["order_pct"] = stt.orders / stt.orders.sum() * 100
    t8 = stt.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(t8.customer_state, t8.order_pct, color=[GREY] * (len(t8) - 1) + [HIGHLIGHT])
    for b, v in zip(bars, t8.order_pct):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=10)
    ax.set_xlim(0, t8.order_pct.max() * 1.15)
    ax.set_xlabel("% dari total order")
    ax.set_title("Porsi order per state", loc="left", fontsize=13, fontweight="bold")
    clean_axes(ax)
    show(fig)