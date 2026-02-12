import { Box } from '@mui/material';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <Box display="flex" minHeight="100vh" bgcolor="#f5f6fa">
      <Sidebar />
      <Box
        flex={1}
        display="flex"
        flexDirection="column"
        sx={{
          minWidth: 0,
          overflow: 'hidden'
        }}
      >
        <TopBar />
        <Box
          component="main"
          flex={1}
          p={3}
          sx={{
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;
