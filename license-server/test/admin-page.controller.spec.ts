import { AdminPageController } from '../src/admin-page.controller';

describe('admin page', () => {
  const html = new AdminPageController().page();

  it('renders the selected operations dashboard and all core sections', () => {
    expect(html).toContain('运营概览');
    expect(html).toContain('会员类型分布');
    expect(html).toContain('快捷生成激活码');
    expect(html).toContain('许可证管理');
    expect(html).toContain('设备管理');
    expect(html).toContain('操作记录');
    expect(html).toContain('版本发布');
  });

  it('keeps the bearer token in page memory instead of browser storage', () => {
    expect(html).toContain("const state={token:''");
    expect(html).not.toMatch(/localStorage|sessionStorage/);
  });
});
