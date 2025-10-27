import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import Layout from "../components/Layout";
import { http } from "../lib/http";
import "../styles/Certificate.css";
import LogoRotaMark from "../images/RotaLogoRedondo.png";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

type CertificatePayload = {
  trail_id: number;
  trail_title: string;
  student_name: string;
  credential_id: string;
  certificate_hash: string;
  issued_at?: string | null;
  verification_url: string;
  qr_code_data_uri: string;
};

const DESIGN_WIDTH = 900;

export default function Certificate() {
  const location = useLocation();

  const [data, setData] = useState<CertificatePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // refs e estados p/ escala responsiva mantendo proporção do desktop
  const certificateRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);
  const [naturalHeight, setNaturalHeight] = useState<number>(0);

  const certHash = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("cert_hash");
  }, [location.search]);

  useEffect(() => {
    async function fetchCertificate() {
      if (!certHash) {
        setError("Certificado não encontrado. Verifique o link recebido.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const verifyBase =
          typeof window !== "undefined" ? window.location.origin : undefined;

        const { data } = await http.get<CertificatePayload>(
          `/certificates/${encodeURIComponent(certHash)}`,
          verifyBase ? { params: { verify_base: verifyBase } } : undefined
        );
        setData(data);
      } catch (err: any) {
        if (err?.response?.status === 404) {
          setError("Certificado não encontrado ou expirado.");
        } else {
          setError("Não foi possível carregar o certificado.");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchCertificate();
  }, [certHash]);

  // Data formatada
  const issuedDate = useMemo(() => {
    if (!data?.issued_at) return null;
    const dt = new Date(data.issued_at);
    if (Number.isNaN(dt.getTime())) return null;
    return dt.toLocaleDateString("pt-BR");
  }, [data?.issued_at]);

  // ---- Medição robusta da altura natural (sem escala) ----
  useLayoutEffect(() => {
    function measure() {
      if (!certificateRef.current) return;
      const el = certificateRef.current;
      const h =
        Math.max(
          el.scrollHeight || 0,
          el.offsetHeight || 0,
          el.getBoundingClientRect?.().height || 0
        ) || 0;
      setNaturalHeight(Math.ceil(h));
    }

    // mede já
    measure();

    // re-mede quando as fontes terminarem de carregar
    if (document.fonts?.ready) {
      document.fonts.ready.then(measure).catch(() => {});
    }

    // re-mede ao carregar as imagens internas (logo/QR)
    const imgs = certificateRef.current?.querySelectorAll("img") ?? [];
    const unsubs: Array<() => void> = [];
    imgs.forEach((img) => {
      if (!img.complete) {
        const onLoad = () => measure();
        const onErr = () => measure();
        img.addEventListener("load", onLoad);
        img.addEventListener("error", onErr);
        unsubs.push(() => {
          img.removeEventListener("load", onLoad);
          img.removeEventListener("error", onErr);
        });
      }
    });

    // Observa mutações no certificado (fallback p/ qualquer mudança de layout)
    const mo = new MutationObserver(() => measure());
    if (certificateRef.current) {
      mo.observe(certificateRef.current, {
        attributes: true,
        childList: true,
        subtree: true,
        characterData: true,
      });
    }

    return () => {
      mo.disconnect();
      unsubs.forEach((u) => u());
    };
  }, [data]);

  // ---- Cálculo da escala: largura E altura da viewport ----
  const recomputeScale = () => {
    if (!stageRef.current) return;
    const rect = stageRef.current.getBoundingClientRect();
    const stageWidth = rect.width;

    // limite por largura (layout fixo em 900px)
    const byWidth = stageWidth / DESIGN_WIDTH;

    // limite por altura disponível da viewport (abaixo do topo do palco)
    let byHeight = 1;
    if (naturalHeight > 0) {
      const viewportH = window.innerHeight;
      // margem inferior mínima para respiro (px)
      const bottomMargin = 16;
      const availableH = Math.max(0, viewportH - rect.top - bottomMargin);
      byHeight = availableH > 0 ? availableH / naturalHeight : 1;
    }

    // escala final
    const next = Math.max(0.01, Math.min(1, byWidth, byHeight));
    setScale(next);
  };

  // Observa largura do palco
  useEffect(() => {
    if (!stageRef.current) return;
    const ro = new ResizeObserver(() => recomputeScale());
    ro.observe(stageRef.current);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recalcula escala quando altura natural muda (conteúdo/ fontes/ imagens)
  useEffect(() => {
    recomputeScale();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [naturalHeight]);

  // Recalcula em resize/rotação de tela
  useEffect(() => {
    const onResize = () => recomputeScale();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Gera PDF a partir de um clone 900px (sem transform) para manter proporção do desktop
async function handleDownload() {
  if (!certificateRef.current || !data) return;
  setDownloadError(null);

  try {
    setDownloading(true);

    // clona apenas o conteúdo do certificado
    const original = certificateRef.current;
    const clone = original.cloneNode(true) as HTMLElement;

    // wrapper off-screen que "congela" o layout em desktop
    const offscreen = document.createElement("div");
    offscreen.style.position = "fixed";
    offscreen.style.left = "-10000px";
    offscreen.style.top = "0";
    offscreen.style.background = "#ffffff";

    const wrapper = document.createElement("div");
    wrapper.style.width = "900px"; // largura de design
    wrapper.className = "certificate-freeze"; // <- força layout desktop no clone

    wrapper.appendChild(clone);
    offscreen.appendChild(wrapper);
    document.body.appendChild(offscreen);

    // aguarda fontes (quando disponível) e imagens do CLONE
    if (document.fonts?.ready) {
      try { await document.fonts.ready; } catch {}
    }
    const imgs = Array.from(wrapper.querySelectorAll("img"));
    await Promise.all(
      imgs.map(
        (img) =>
          new Promise<void>((res) => {
            if (img.complete) return res();
            img.addEventListener("load", () => res(), { once: true });
            img.addEventListener("error", () => res(), { once: true });
          })
      )
    );

    // pequeno delay para layout assentar no mobile
    await new Promise((r) => setTimeout(r, 30));

    const canvas = await html2canvas(clone, {
      scale: 3,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
    });

    document.body.removeChild(offscreen);

    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF({
      orientation: "landscape",
      unit: "mm",
      format: "a4",
    });

    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const imgProps = pdf.getImageProperties(imgData);
    const imgRatio = imgProps.height / imgProps.width;

    let renderWidth = pdfWidth;
    let renderHeight = pdfWidth * imgRatio;
    if (renderHeight > pdfHeight) {
      renderHeight = pdfHeight;
      renderWidth = renderHeight / imgRatio;
    }
    const xOffset = (pdfWidth - renderWidth) / 2;
    const yOffset = (pdfHeight - renderHeight) / 2;

    pdf.addImage(imgData, "PNG", xOffset, yOffset, renderWidth, renderHeight);
    pdf.save(`certificado-${data.certificate_hash}.pdf`);
  } catch (err) {
    console.error("Falha ao gerar PDF do certificado", err);
    setDownloadError("Não foi possível gerar o PDF agora. Tente novamente.");
  } finally {
    setDownloading(false);
  }
}

  return (
    <Layout>
      <section className="certificate-page">
        <div className="certificate-container">
          {loading ? (
            <div className="certificate-status">Carregando certificado…</div>
          ) : error ? (
            <div className="certificate-status error">{error}</div>
          ) : data ? (
            <>
              <h1 className="certificate-title">Certificado de conclusão</h1>

              <div className="certificate-wrapper">
                {/* PALCO que calcula a escala e reserva altura */}
                <div
                  className="certificate-stage"
                  ref={stageRef}
                  style={{
                    height:
                      naturalHeight && scale
                        ? Math.ceil(naturalHeight * scale)
                        : undefined,
                  }}
                >
                  {/* Elemento que recebe o transform: scale(...) */}
                  <div
                    className="certificate-scale certificate-freeze"
                    style={{ transform: `scale(${scale})` }}
                  >
                    <div className="certificate-frame" ref={certificateRef}>
                      <div className="certificate-border">
                        <div className="certificate-inner">
                          <header className="sheet-header">
                            <div className="sheet-brand">
                              <img
                                src={LogoRotaMark}
                                alt="Marca Projeto Rota"
                              />
                            </div>
                            <div className="sheet-credential">{`#${data.credential_id}`}</div>
                          </header>

                          <div className="sheet-headline">
                            <h2 className="sheet-title">CERTIFICADO</h2>
                            <span className="sheet-subtitle">de conclusão</span>
                          </div>

                          <section className="sheet-body">
                            <p className="sheet-text">
                              Este certificado comprova que
                            </p>
                            <h3 className="sheet-name">{data.student_name}</h3>
                            <span
                              className="sheet-name-line"
                              aria-hidden="true"
                            ></span>
                            <p className="sheet-text">concluiu o curso</p>
                            <h4 className="sheet-course">
                              {data.trail_title}
                            </h4>
                          </section>

                          <div className="sheet-divider" aria-hidden="true" />

                          <footer className="sheet-footer">
                            <div className="sheet-qr">
                              <img
                                src={data.qr_code_data_uri}
                                alt="Código QR para validar o certificado"
                              />
                              <span className="sheet-qr-caption">
                                Verifique com o QR Code
                              </span>
                            </div>
                            <div className="sheet-issue">
                              <span className="sheet-label">
                                Data de emissão
                              </span>
                              <span className="sheet-value">
                                {issuedDate ?? "--"}
                              </span>

                              <span className="sheet-label">
                                Código da credencial
                              </span>
                              <span className="sheet-value">{`#${data.credential_id}`}</span>
                            </div>
                            <div className="sheet-signature">
                              <span
                                className="sheet-signature-line"
                                aria-hidden="true"
                              />
                              <span className="sheet-signature-name">
                                Equipe ENACTUS Mackenzie
                              </span>
                              <span className="sheet-signature-role">
                                Projeto Rota
                              </span>
                            </div>
                          </footer>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Meta e ações */}
                <div className="certificate-meta">
                  <div>
                    <strong>ID da credencial</strong>
                    <span>{`#${data.credential_id}`}</span>
                  </div>
                  <div>
                    <strong>Emitida pela</strong>
                    <span>ROTA - ENACTUS Mackenzie</span>
                  </div>
                  <div>
                    <strong>Data de emissão</strong>
                    <span>{issuedDate ?? "--"}</span>
                  </div>
                  <div>
                    <strong>URL de verificação</strong>
                    <a
                      href={data.verification_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="certificate-link"
                    >
                      {data.verification_url}
                    </a>
                  </div>
                </div>

                <div className="certificate-actions">
                  <button
                    type="button"
                    className="certificate-download"
                    onClick={handleDownload}
                    disabled={downloading}
                  >
                    {downloading ? "Gerando PDF…" : "Baixar certificado (PDF)"}
                  </button>
                </div>

                {downloadError ? (
                  <div className="certificate-download-error" role="alert">
                    {downloadError}
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      </section>
    </Layout>
  );
}
