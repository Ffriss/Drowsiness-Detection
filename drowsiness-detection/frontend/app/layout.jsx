import { IBM_Plex_Sans_Thai } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const font = IBM_Plex_Sans_Thai({
  subsets: ["thai", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

export const metadata = {
  title: "ตรวจจับการหลับในและการละสายตา",
  description: "Driver Drowsiness and Distraction Detection System Using Deep Learning-Based Eye State Classification and Head Pose Estimation",
};

export default function RootLayout({ children }) {
  return (
    <html lang="th" className={font.variable}>
      <body className="font-sans antialiased">
        <div className="flex min-h-screen flex-col md:flex-row">
          <Nav />
          <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
