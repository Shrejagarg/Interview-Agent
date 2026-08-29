# Visual and Canvas Testing

## Why Visual/Canvas Testing Is Different

DOM-based tests query elements by role, text, or test ID. Canvas and WebGL components render to an opaque bitmap — there are no DOM elements inside the canvas to query. Testing them requires a different strategy:

1. **Contract testing** — assert that the right drawing functions were called with the right data (fast, deterministic, runs in jsdom)
2. **Visual regression testing** — compare rendered pixel output against a baseline image (slower, catches visual bugs, needs a rendering context)

Neither alone is sufficient. Contract tests catch logic bugs. Visual regression tests catch rendering bugs.

---

## Canvas Mocking with vitest-canvas-mock

### Setup

```bash
npm install -D vitest-canvas-mock
```

In your `setup.ts`:

```ts
import 'vitest-canvas-mock';
```

This patches `HTMLCanvasElement.prototype.getContext` to return a mock 2D context that records all draw calls.

### What It Gives You

The mock context tracks every method call. You can assert on what was drawn without actual rendering:

```tsx
import { render } from '../test-utils';
import { BarChart } from './BarChart';

describe('BarChart', () => {
  it('draws a bar for each data point', () => {
    const data = [
      { label: 'Jan', value: 10 },
      { label: 'Feb', value: 20 },
      { label: 'Mar', value: 30 },
    ];

    const { container } = render(<BarChart data={data} width={300} height={200} />);
    const canvas = container.querySelector('canvas')!;
    const ctx = canvas.getContext('2d')!;

    // Assert fillRect was called for each bar
    const drawCalls = (ctx as any).__getDrawCalls();
    const fillRectCalls = drawCalls.filter(
      (call: any) => call.type === 'fillRect'
    );
    expect(fillRectCalls).toHaveLength(3);
  });

  it('draws axis labels', () => {
    const data = [{ label: 'Jan', value: 10 }];
    const { container } = render(<BarChart data={data} width={300} height={200} />);
    const ctx = container.querySelector('canvas')!.getContext('2d')!;

    const drawCalls = (ctx as any).__getDrawCalls();
    const textCalls = drawCalls.filter(
      (call: any) => call.type === 'fillText'
    );
    expect(textCalls.some((c: any) => c.props.text === 'Jan')).toBe(true);
  });
});
```

### Limitations

No actual rendering occurs. You test that the right drawing commands were issued, not that the visual output is correct. A wrong coordinate in `fillRect` will not produce a visually wrong chart in this test — use pixel matching for that.

---

## WebGL Context Mocking

`vitest-canvas-mock` partially covers WebGL. For deeper control, create manual mocks.

### Mock Pattern for getContext('webgl')

```tsx
function createMockWebGLContext() {
  return {
    createProgram: vi.fn(() => ({})),
    createShader: vi.fn(() => ({})),
    shaderSource: vi.fn(),
    compileShader: vi.fn(),
    getShaderParameter: vi.fn(() => true),
    attachShader: vi.fn(),
    linkProgram: vi.fn(),
    getProgramParameter: vi.fn(() => true),
    useProgram: vi.fn(),
    createBuffer: vi.fn(() => ({})),
    bindBuffer: vi.fn(),
    bufferData: vi.fn(),
    getAttribLocation: vi.fn(() => 0),
    enableVertexAttribArray: vi.fn(),
    vertexAttribPointer: vi.fn(),
    getUniformLocation: vi.fn(() => ({})),
    uniform1f: vi.fn(),
    uniform2f: vi.fn(),
    uniform3f: vi.fn(),
    uniform4f: vi.fn(),
    uniformMatrix4fv: vi.fn(),
    viewport: vi.fn(),
    clearColor: vi.fn(),
    clear: vi.fn(),
    drawArrays: vi.fn(),
    drawElements: vi.fn(),
    enable: vi.fn(),
    disable: vi.fn(),
    getExtension: vi.fn(() => null),
    canvas: document.createElement('canvas'),
  };
}

vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
  (contextId: string) => {
    if (contextId === 'webgl' || contextId === 'webgl2') {
      return createMockWebGLContext() as any;
    }
    return null;
  }
);
```

### Mock Pattern for Three.js

```tsx
vi.mock('three', async (importOriginal) => {
  const THREE = await importOriginal<typeof import('three')>();
  return {
    ...THREE,
    WebGLRenderer: vi.fn().mockImplementation(() => ({
      render: vi.fn(),
      setSize: vi.fn(),
      setPixelRatio: vi.fn(),
      setClearColor: vi.fn(),
      dispose: vi.fn(),
      domElement: document.createElement('canvas'),
    })),
  };
});
```

---

## Testing NGL Viewer (Molecule Visualization)

NGL Viewer renders 3D molecular structures in a WebGL canvas. Key classes: `Stage`, `Component`, `RepresentationElement`.

### Strategy A: Contract Testing (Recommended for Unit/Integration)

Mock the `Stage` class and assert that your component calls the right NGL methods:

```tsx
const mockRepresentation = { setParameters: vi.fn(), dispose: vi.fn() };
const mockComponent = {
  addRepresentation: vi.fn(() => mockRepresentation),
  removeAllRepresentations: vi.fn(),
  autoView: vi.fn(),
};
const mockStage = {
  loadFile: vi.fn(() => Promise.resolve(mockComponent)),
  handleResize: vi.fn(),
  dispose: vi.fn(),
  signals: {
    hovered: { add: vi.fn() },
    clicked: { add: vi.fn() },
  },
  mouseControls: { add: vi.fn() },
};

vi.mock('ngl', () => ({
  Stage: vi.fn(() => mockStage),
}));

import { render, screen, waitFor } from '../test-utils';
import { MoleculeViewer } from './MoleculeViewer';

describe('MoleculeViewer', () => {
  it('loads the PDB file from RCSB', async () => {
    render(<MoleculeViewer pdbId="1crn" />);
    await waitFor(() => {
      expect(mockStage.loadFile).toHaveBeenCalledWith(
        'rcsb://1crn',
        expect.any(Object)
      );
    });
  });

  it('applies the requested representation', async () => {
    render(<MoleculeViewer pdbId="1crn" representation="cartoon" />);
    await waitFor(() => {
      expect(mockComponent.addRepresentation).toHaveBeenCalledWith(
        'cartoon',
        expect.any(Object)
      );
    });
  });

  it('changes representation when prop changes', async () => {
    const { rerender } = render(
      <MoleculeViewer pdbId="1crn" representation="cartoon" />
    );
    await waitFor(() => {
      expect(mockComponent.addRepresentation).toHaveBeenCalledWith(
        'cartoon',
        expect.any(Object)
      );
    });
    rerender(<MoleculeViewer pdbId="1crn" representation="ball+stick" />);
    await waitFor(() => {
      expect(mockComponent.removeAllRepresentations).toHaveBeenCalled();
      expect(mockComponent.addRepresentation).toHaveBeenCalledWith(
        'ball+stick',
        expect.any(Object)
      );
    });
  });

  it('auto-views after loading', async () => {
    render(<MoleculeViewer pdbId="1crn" />);
    await waitFor(() => {
      expect(mockComponent.autoView).toHaveBeenCalled();
    });
  });

  it('registers hover callback', async () => {
    const onHover = vi.fn();
    render(<MoleculeViewer pdbId="1crn" onAtomHover={onHover} />);
    await waitFor(() => {
      expect(mockStage.signals.hovered.add).toHaveBeenCalled();
    });
  });

  it('disposes stage on unmount', () => {
    const { unmount } = render(<MoleculeViewer pdbId="1crn" />);
    unmount();
    expect(mockStage.dispose).toHaveBeenCalled();
  });
});
```

### Strategy B: Visual Regression (For CI/Nightly)

Use headless GL to get a real WebGL context in Node and compare rendered output pixel-by-pixel. See the Headless GL section below.

### Testing Interaction Callbacks

NGL emits events like `hoverAtom` and `clickPick`. Test that your component handles them:

```tsx
it('shows tooltip on atom hover', async () => {
  render(<MoleculeViewer pdbId="1crn" showTooltip />);

  await waitFor(() => {
    expect(mockStage.signals.hovered.add).toHaveBeenCalled();
  });

  const hoverHandler = mockStage.signals.hovered.add.mock.calls[0][0];
  act(() => {
    hoverHandler({
      atom: { resname: 'THR', resno: 1, chainname: 'A', element: 'CA' },
    });
  });

  expect(screen.getByText('THR 1:A (CA)')).toBeInTheDocument();
});
```

---

## Pixel Matching with jest-image-snapshot {#pixel-matching}

### Setup

```bash
npm install -D jest-image-snapshot @types/jest-image-snapshot
```

In your `setup.ts`:

```ts
import { toMatchImageSnapshot } from 'jest-image-snapshot';
expect.extend({ toMatchImageSnapshot });
```

### Basic Usage

```tsx
it('renders chart correctly', () => {
  const { container } = render(<BarChart data={sampleData} width={400} height={300} />);
  const canvas = container.querySelector('canvas')!;

  const dataUrl = canvas.toDataURL('image/png');
  const base64 = dataUrl.split(',')[1];
  const buffer = Buffer.from(base64, 'base64');

  expect(buffer).toMatchImageSnapshot();
});
```

### Threshold Configuration

Pixel-perfect comparisons are brittle. Configure thresholds to tolerate acceptable variance:

```tsx
expect(buffer).toMatchImageSnapshot({
  failureThreshold: 0.01,
  failureThresholdType: 'percent',
  customDiffConfig: { threshold: 0.1 },
  blur: 1,
});
```

| Parameter | Recommended Value | Explanation |
|-----------|------------------|-------------|
| `failureThreshold` | 0.01 (1%) | Percentage of pixels that can differ |
| `failureThresholdType` | `'percent'` | Use percent for responsive, pixel count for fixed-size |
| `customDiffConfig.threshold` | 0.1 | pixelmatch sensitivity (0-1). 0.1 tolerates antialiasing |
| `blur` | 1 | Gaussian blur radius to smooth sub-pixel differences |

### Updating Baselines

```bash
npx vitest run --update
```

Or delete the `__image_snapshots__` directory to regenerate all baselines.

### CI Considerations

Rendering differs across operating systems. Strategies:

1. **Pin the CI OS** — use the same Linux distro/version in CI and locally
2. **Docker** — run visual tests in a Docker container for consistency
3. **Higher thresholds** — set `failureThreshold: 0.02-0.05` for cross-platform CI
4. **Separate visual test suite** — run pixel tests only in CI where the environment is controlled

---

## Headless GL Strategy

The `gl` npm package provides a software-based WebGL implementation for Node.js — no GPU needed.

### Setup

```bash
npm install -D gl
```

On CI (Ubuntu): `apt-get install -y libgl1-mesa-dev libxi-dev libxext-dev`

### Usage

```tsx
import createContext from 'gl';
import { PNG } from 'pngjs';

function renderToBuffer(width: number, height: number): Buffer {
  const glContext = createContext(width, height);

  // Render your scene using the headless context
  const pixels = new Uint8Array(width * height * 4);
  glContext.readPixels(0, 0, width, height, glContext.RGBA, glContext.UNSIGNED_BYTE, pixels);

  // WebGL reads bottom-to-top; flip vertically for PNG
  const flipped = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    const srcRow = y * width * 4;
    const dstRow = (height - 1 - y) * width * 4;
    flipped.set(pixels.subarray(srcRow, srcRow + width * 4), dstRow);
  }

  const png = new PNG({ width, height });
  png.data = Buffer.from(flipped);
  return PNG.sync.write(png);
}

it('renders the molecule correctly', () => {
  const buffer = renderToBuffer(800, 600);
  expect(buffer).toMatchImageSnapshot({
    failureThreshold: 0.02,
    failureThresholdType: 'percent',
  });
});
```

### Bridging to Three.js

```tsx
import createContext from 'gl';
import * as THREE from 'three';

const glContext = createContext(800, 600);
const renderer = new THREE.WebGLRenderer({
  context: glContext as any,
  antialias: false, // disable for deterministic output
});
renderer.setSize(800, 600);
```

### Limitations

- **WebGL 1 only** — headless-gl does not support WebGL2. For WebGL2 content, use Playwright for visual regression and keep Vitest tests focused on contract testing.
- **No shader extensions** — some advanced shaders may fail to compile. Keep headless GL tests focused on geometry and basic rendering.
- **Performance** — software rendering is slower than GPU. Keep scene complexity low in tests.

---

## Summary: Which Strategy When?

| Scenario | Strategy | Speed | Catches |
|----------|----------|-------|---------|
| Component calls canvas methods correctly | Contract test (vitest-canvas-mock) | Fast | Logic bugs |
| Component calls WebGL/NGL methods correctly | Contract test (mock Stage/Renderer) | Fast | Integration bugs |
| Rendered output looks correct | Pixel snapshot (jest-image-snapshot) | Medium | Visual regressions |
| WebGL scene renders correctly | Headless GL + pixel snapshot | Slow | Rendering bugs |
| Complex 3D interactions | Contract test for callbacks | Fast | Event handling bugs |
| Cross-browser visual consistency | Playwright visual comparison (E2E) | Slowest | Platform-specific bugs |
