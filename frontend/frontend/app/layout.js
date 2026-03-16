import "../styles/globals.css";

export const metadata = {
  title: "EEEVA",
  description: "EEEVA Syllabus Assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}