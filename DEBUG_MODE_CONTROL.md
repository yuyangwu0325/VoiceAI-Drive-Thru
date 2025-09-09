# Debug Mode Control - Grill Talk

## 🎯 **Overview**

The debug status labels ("Order Display: Connected" and "Voice: Connected") are now hidden by default in production and can be controlled through multiple methods for debugging purposes.

## 🔧 **Control Methods**

### **1. Environment Variables (Recommended)**

#### **Production (Hidden by default)**
```bash
# In .env.production file (already created)
REACT_APP_DEBUG_MODE=false
```

#### **Development (Shown by default)**
```bash
# In .env.development file (already created)
REACT_APP_DEBUG_MODE=true
```

#### **Manual Override**
```bash
# Create .env.local file to override for any environment
REACT_APP_DEBUG_MODE=true   # Show debug info
REACT_APP_DEBUG_MODE=false  # Hide debug info
```

### **2. Keyboard Shortcut (Runtime Toggle)**

While the application is running, press:
```
Ctrl + Shift + D
```

This will toggle the debug status labels on/off and log the current state to the browser console.

### **3. Build-time Configuration**

#### **Production Build (Debug Hidden)**
```bash
npm run build
# Uses .env.production settings (debug mode OFF)
```

#### **Development Build (Debug Visible)**
```bash
npm start
# Uses .env.development settings (debug mode ON)
```

## 📋 **Current Behavior**

### **Default States**
- **Development Mode**: Debug labels visible
- **Production Build**: Debug labels hidden
- **Runtime**: Can be toggled with Ctrl+Shift+D

### **Debug Labels Show**
- "Order Display: Connected/Disconnected" - WebSocket connection status
- "Voice: Connected/Disconnected" - Voice WebRTC connection status

### **When Hidden**
- Clean production interface with only the power button
- Professional appearance for customer-facing displays
- All functionality remains intact

## 🚀 **Deployment Scenarios**

### **For Production Restaurant Use**
```bash
# Build for production (debug hidden)
npm run build

# Deploy the build folder
# Debug labels will be hidden by default
# Staff can still use Ctrl+Shift+D if needed for troubleshooting
```

### **For Development/Testing**
```bash
# Run in development mode (debug visible)
npm start

# Or create .env.local with REACT_APP_DEBUG_MODE=true
# Then run: npm run build
```

### **For Demo/Training**
```bash
# Create .env.local file:
echo "REACT_APP_DEBUG_MODE=true" > .env.local

# Build with debug visible
npm run build
```

## 🔍 **Troubleshooting**

### **Debug Labels Not Showing When Expected**
1. Check if `.env.local` exists and overrides other settings
2. Verify `REACT_APP_DEBUG_MODE` value in environment files
3. Try the keyboard shortcut: Ctrl+Shift+D
4. Check browser console for debug mode status messages

### **Debug Labels Showing in Production**
1. Ensure `.env.production` has `REACT_APP_DEBUG_MODE=false`
2. Remove any `.env.local` file that might override settings
3. Rebuild the application: `npm run build`
4. Use keyboard shortcut to toggle off: Ctrl+Shift+D

## 📁 **Files Created/Modified**

### **New Files**
- `frontend/.env.production` - Production environment config
- `frontend/.env.development` - Development environment config

### **Modified Files**
- `frontend/src/App.js` - Added debug mode logic and keyboard shortcut
- `frontend/src/App.css` - Cleaned up unused debug button styles

## 🎉 **Result**

Your Grill Talk interface now has:
- ✅ **Clean production appearance** - No debug clutter for customers
- ✅ **Easy debugging access** - Multiple ways to show/hide debug info
- ✅ **Flexible configuration** - Environment-based control
- ✅ **Runtime control** - Keyboard shortcut for instant toggle
- ✅ **Professional deployment** - Ready for restaurant use

Perfect for both development debugging and production deployment! 🚀
