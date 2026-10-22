import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Photos from "./pages/Photos";
import PhotoCollection from "./pages/PhotoCollection";
import NotFound from "./pages/NotFound";
import { ScrollToHash } from "@/components/site/ScrollToHash";
import { IntroGate } from "@/components/intro/IntroGate";

// The admin is only ever opened by its secret URL, so keep it out of the public bundle.
const AdminApp = lazy(() => import("./admin/AdminApp"));

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <ScrollToHash />
        <IntroGate />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/photos" element={<Photos />} />
          <Route path="/photos/:slug" element={<PhotoCollection />} />
          <Route
            path="/a/:prefix/*"
            element={
              <Suspense fallback={null}>
                <AdminApp />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
