import Header from "./Header";
import Footer from "./Footer";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main className="site-content">
        <div className="container">{children}</div>
      </main>
      <Footer />
    </>
  );
}
